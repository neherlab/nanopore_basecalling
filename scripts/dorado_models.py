"""Turn the model and the modifications a run asks for into dorado model names.

Dorado carries its whole model catalogue inside the binary: `dorado download
--list-structured` prints it as json in well under a second and reaches no network, which
is what makes it usable here — the compute nodes have no internet, and the workflow is
re-parsed on every one of them.

That catalogue is the single source of truth for all three questions this module answers:
what `sup@v5.2.0` means for a given flow cell, which model calls a given modification, and
whether two modifications can be called in the same run. It is read at parse time, so a
mistake is reported before any job is submitted rather than an hour later on a GPU node.

Imported by the Snakefile rather than run as a script, like `utils`.
"""

import json
import re
import subprocess
import sys

# A model named as <tier>@<version>, with the chemistry left off — "sup@v5.2.0".
SHORT_MODEL = re.compile(r"^[a-z]+@v[0-9.]+$")


class ModelError(Exception):
    "A model or a modification that dorado could not be asked for."


def catalogue(dorado_bin):
    "Dorado's model catalogue, keyed by chemistry group. Needs no network."
    try:
        listing = subprocess.check_output(
            [dorado_bin, "download", "--list-structured"], stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError) as err:
        raise ModelError(
            f"could not read the model list from '{dorado_bin}' ({err}). Check "
            "'dorado_bin' in config/config.yaml, and see docs/setup.md."
        )
    return json.loads(listing)


def resolve(dorado_bin, model, modifications, flow_cell, kit):
    """The full dorado model names a run needs: the simplex model, then one per modification.

    `model` is either a full model name or the short <tier>@<version> form, in which case
    the chemistry comes from the flow cell and the kit. `modifications` is the comma
    separated list of modification codes from the config, empty for a plain run.
    """
    groups = catalogue(dorado_bin)

    if SHORT_MODEL.match(model):
        group_name, group = _group_of_run(groups, flow_cell, kit)
        simplex = _simplex_from_tier(group_name, group, model)
    else:
        # A full name carries its own chemistry, so it works even for a flow cell or a kit
        # the catalogue does not list. That is the point of keeping the long form.
        group_name, group = _group_of_model(groups, model)
        simplex = model
        if flow_cell not in group["flowcells"]:
            _warn(
                f"model '{simplex}' is for {group_name}, which does not cover flow cell "
                f"'{flow_cell}'. Basecalling with a model that does not match the "
                "chemistry gives poor reads."
            )

    entry = group["simplex_models"][simplex]
    if entry.get("outdated"):
        _warn(f"model '{simplex}' is marked outdated by dorado; a newer one exists.")

    return simplex, _resolve_mods(entry, simplex, _split_codes(modifications))


# ---------------------------------------------------------------------------
# Finding the simplex model
# ---------------------------------------------------------------------------


def _group_of_run(groups, flow_cell, kit):
    "The chemistry group a run belongs to. Both the flow cell and the kit are needed."
    # The flow cell alone is not enough: FLO-MIN114 appears in two groups, which only the
    # kit separates.
    matches = [
        name
        for name, group in groups.items()
        if flow_cell in group["flowcells"] and kit in group["kits"]
    ]
    if len(matches) == 1:
        return matches[0], groups[matches[0]]
    if len(matches) > 1:
        raise ModelError(
            f"flow cell '{flow_cell}' with kit '{kit}' matches several chemistries "
            f"({', '.join(matches)}), so a '<tier>@<version>' model is ambiguous. Give "
            "'model' as a full dorado model name instead."
        )
    raise ModelError(
        f"dorado knows no chemistry for flow cell '{flow_cell}' with kit '{kit}', so a "
        f"'<tier>@<version>' model cannot be resolved. Either correct 'flow_cell' and "
        f"'kit' in the run's run.yaml, or give 'model' as a full dorado model name. "
        f"The combinations dorado knows:\n{_group_summary(groups)}"
    )


def _group_of_model(groups, model):
    "The chemistry group a full model name belongs to."
    for name, group in groups.items():
        if model in group["simplex_models"]:
            return name, group
    current = sorted(
        name
        for group in groups.values()
        for name, entry in group["simplex_models"].items()
        if not entry.get("outdated")
    )
    raise ModelError(
        f"dorado has no model called '{model}'. Give the short '<tier>@<version>' form, "
        f"e.g. 'sup@v5.2.0', or one of the current full names:\n"
        + "\n".join(f"  {name}" for name in current)
    )


def _simplex_from_tier(group_name, group, model):
    "The full name of the <tier>@<version> model inside one chemistry group."
    tier, version = model.split("@")
    matches = [
        name
        for name, entry in group["simplex_models"].items()
        if entry.get("variant") == tier and name.endswith("@" + version)
    ]
    if not matches:
        raise ModelError(
            f"dorado has no '{model}' model for {group_name}. Available there:\n"
            + "\n".join(
                f"  {entry['variant']}@{name.rsplit('@', 1)[-1]}"
                + ("   (outdated)" if entry.get("outdated") else "")
                for name, entry in group["simplex_models"].items()
            )
        )
    return matches[0]


def _group_summary(groups):
    "One line per chemistry group, for the error message when a run matches none."
    return "\n".join(
        f"  {name}\n"
        f"    flow cells: {', '.join(group['flowcells'])}\n"
        f"    kits: {', '.join(group['kits'])}"
        for name, group in groups.items()
    )


# ---------------------------------------------------------------------------
# Finding the modified-base models
# ---------------------------------------------------------------------------


def _split_codes(modifications):
    "The modification codes as a list, from the comma separated string in the config."
    if modifications is None:
        return []
    if isinstance(modifications, str):
        codes = modifications.split(",")
    elif isinstance(modifications, (list, tuple)):
        codes = modifications
    else:
        raise ModelError(
            f"'modifications' should be a comma separated list of modification codes, "
            f"e.g. '4mC_5mC,6mA', but is {modifications!r}."
        )
    return [str(code).strip() for code in codes if str(code).strip()]


def _resolve_mods(entry, simplex, codes):
    "One modified-base model name per requested code, checked for compatibility."
    available = entry.get("modified_models", {})
    chosen = {}
    for code in codes:
        if code in chosen:
            raise ModelError(f"'{code}' is asked for twice in 'modifications'.")
        chosen[code] = _pick_mod(available, simplex, code)
    _check_compatible(available, chosen)
    return list(chosen.values())


def _pick_mod(available, simplex, code):
    "The model calling one modification, taking the current version unless one is pinned."
    variant, _, pin = code.partition("@")
    if pin and not pin.startswith("v"):
        pin = "v" + pin

    candidates = [
        name for name, mod in available.items() if mod.get("variant") == variant
    ]
    if not candidates:
        variants = sorted({mod["variant"] for mod in available.values()})
        raise ModelError(
            f"dorado has no model to call '{code}' with '{simplex}'. "
            + (
                f"Modifications available for this model: {', '.join(variants)}."
                if variants
                else "This model calls no modified bases at all — try a hac or sup model."
            )
        )

    if pin:
        pinned = [name for name in candidates if name.endswith("@" + pin)]
        if not pinned:
            versions = ", ".join(sorted(name.rsplit("@", 1)[-1] for name in candidates))
            raise ModelError(
                f"dorado has no '{variant}' model at version '{pin}' for '{simplex}'. "
                f"Versions available: {versions}."
            )
        candidates = pinned

    # Several versions of the same modification are usually one current and one retired,
    # so prefer whatever dorado has not marked outdated and take the newest of those.
    current = [name for name in candidates if not available[name].get("outdated")]
    return max(current or candidates, key=_version_key)


def _check_compatible(available, chosen):
    """Refuse two modifications dorado could not call together.

    Dorado's rule is one modified-base model per canonical base — two models whose motifs
    overlap on the same base cannot run in one pass — and all the C models it ships have
    context C or CG, which always overlap. It only finds this out once the models are
    loaded, i.e. well inside the basecall job, so the check is worth repeating here.
    """
    by_base = {}
    for name in chosen.values():
        by_base.setdefault(available[name]["canonical_base"], []).append(name)

    for base, names in sorted(by_base.items()):
        if len(names) > 1:
            contexts = ", ".join(f"{n} on {available[n]['context']}" for n in names)
            raise ModelError(
                f"{len(names)} of the requested modifications are called on '{base}' "
                f"({contexts}), and dorado allows only one per canonical base. Keep one "
                "of them, or basecall twice."
            )


def _version_key(name):
    "Sort key for the trailing @vX.Y of a model name, so v3 comes after v2.0.1."
    version = name.rsplit("@v", 1)[-1]
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def _warn(message):
    "A note that does not stop the run, in the style of the Snakefile's own errors."
    print(f"Warning: {message}", file=sys.stderr)
