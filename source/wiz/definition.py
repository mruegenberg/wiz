# :coding: utf-8

import os
import re
import copy
import collections
import json

from packaging.requirements import Requirement, InvalidRequirement
from packaging.version import Version, InvalidVersion
import mlog

import wiz.exception


def fetch(paths, max_depth=None):
    """Return mapping from all environment definitions available under *paths*.

    :func:`discover` available environments under *paths*, searching recursively
    up to *max_depth*.

    """
    mapping = dict()

    for definition in discover(paths, max_depth=max_depth):
        base_version = definition.version.base_version
        mapping.setdefault(definition.identifier, {})
        mapping[definition.identifier][base_version] = definition

    return mapping


def search(requirement, paths, max_depth=None):
    """Return mapping from environment definitions matching *requirement*.

    *requirement* is an instance of :class:`packaging.requirements.Requirement`.

    :func:`~wiz.definition.discover` available environments under *paths*,
    searching recursively up to *max_depth*.

    """
    logger = mlog.Logger(__name__ + ".search")
    logger.info(
        "Search environment definition definitions matching '{}'"
        .format(requirement)
    )

    mapping = dict()

    for definition in discover(paths, max_depth=max_depth):
        if (
            requirement.name.lower() in definition.identifier.lower() or
            requirement.name.lower() in definition.description.lower()
        ):
            if definition.version in requirement.specifier:
                base_version = definition.version.base_version
                mapping.setdefault(definition.identifier, {})
                mapping[definition.identifier][base_version] = definition

    return mapping


def get(requirement, definition_mapping):
    """Get best matching :class:`Definition` instances for *requirement*.

    The best matching definition version corresponding to the *requirement*
    will be returned.

    If this definition contains variants, the ordered list of combined
    definition variants will be returned. If one variant is explicitly
    requested, only the corresponding combined definition variant will be
    returned. Otherwise, the required definition will be returned

    *requirement* is an instance of :class:`packaging.requirements.Requirement`.

    *definition_mapping* is a mapping regrouping all available environment
    definition associated with their unique identifier.

    :exc:`wiz.exception.IncorrectRequirement` is raised if the
    requirement can not be resolved.

    """
    if requirement.name not in definition_mapping:
        raise wiz.exception.IncorrectRequirement(requirement)

    definition = None

    # Sort the definition so that the highest version is first. It is more
    # efficient to do the sorting when a definition is required rather than for
    # all the definitions found in the registries...
    sorted_definitions = sorted(
        definition_mapping[requirement.name].values(),
        key=lambda _definition: _definition.version,
        reverse=True
    )

    # Get the best matching definition.
    for _definition in sorted_definitions:
        if _definition.version in requirement.specifier:
            definition = _definition
            break

    if definition is None:
        raise wiz.exception.IncorrectRequirement(requirement)

    # Extract variants from definitions.
    variants = definition.get("variant", [])

    # Simply return the main definition if no variants is available.
    if len(variants) == 0:
        return [definition]

    # Extract and return the requested variant if necessary.
    elif len(requirement.extras) > 0:
        variant_identifier = next(iter(requirement.extras))
        variant_mapping = reduce(
            lambda res, mapping: dict(res, **{mapping["identifier"]: mapping}),
            variants, {}
        )

        if variant_identifier not in variant_mapping.keys():
            raise wiz.exception.IncorrectRequirement(
                "The variant '{}' could not been resolved for '{}'.".format(
                    variant_identifier, requirement.name
                )
            )

        return [combine(definition, variant_mapping[variant_identifier])]

    # Otherwise, extract and return all possible variants.
    else:
        return map(lambda variant: combine(definition, variant), variants)


def combine(definition1, definition2):
    """Return combined definition from *definition1* and *definition2*

    *definition1* and *definition2* must be valid
    :class:`~wiz.definition.Definition` instances.

    In case of conflicted elements in both definitions, the elements from the
    *definition2* will have priority over elements from *definition1*.

    The 'identifier' keyword from *definition2* will be set as a 'variant'
    keyword of the combined definition.

    """
    definition = copy.deepcopy(definition1)
    definition["variant"] = definition2.get("identifier")

    definition["system"] = combine_system(definition1, definition2)
    definition["commands"] = combine_commands(definition1, definition2)
    definition["environ"] = combine_environment(definition1, definition2)
    definition["requirement"] = (
        definition1.get("requirement", []) + definition2.get("requirement", [])
    )
    return definition


def combine_commands(definition1, definition2):
    """Return combined commands from *definition1* and *definition2*.

    *definition1* and *definition2* must be valid
    :class:`~wiz.definition.Definition` instances.

    If a command exists in both "commands" mappings, the value from
    *definition2* will have priority over elements from *definition1*.::

        >>> combine_system(
        ...     Definition({"commands": {"app": "App1.1 --run"})
        ...     Definition({"commands": {"app": "App2.1"}})
        ... )

        {"app": "App2.1"}

    """
    logger = mlog.Logger(__name__ + ".combine_commands")

    commands = {}

    commands1 = definition1.get("system", {})
    commands2 = definition2.get("system", {})

    for command in set(commands1.keys() + commands2.keys()):
        value1 = commands1.get(command)
        value2 = commands2.get(command)

        if value1 is not None and value2 is not None:
            logger.warning(
                "The '{key}' command is being overridden in "
                "definition '{identifier}' [{version}]".format(
                    key=command,
                    identifier=definition2.identifier,
                    version=definition2.version
                )
            )
            commands[command] = str(value2)

        else:
            commands[command] = str(value1 or value2)

    return commands


def combine_system(definition1, definition2):
    """Return combined system from *definition1* and *definition2*.

    *definition1* and *definition2* must be valid
    :class:`~wiz.definition.Definition` instances.

    If a keyword exists in both "system" mappings, the value from
    *definition2* will have priority over elements from *definition1*.::

        >>> combine_system(
        ...     Definition({"system": {"platform": "linux", "arch": "x86_64"})
        ...     Definition({"system": {"platform": "macOS"}})
        ... )

        {"platform": "macOS", "arch": "x86_64"}

    """
    logger = mlog.Logger(__name__ + ".combine_system")

    system = {}

    system1 = definition1.get("system", {})
    system2 = definition2.get("system", {})

    for key in set(system1.keys() + system2.keys()):
        value1 = system1.get(key)
        value2 = system2.get(key)

        if value1 is not None and value2 is not None:
            logger.warning(
                "The '{key}' system is being overridden in "
                "definition '{identifier}' [{version}]".format(
                    key=key,
                    identifier=definition2.identifier,
                    version=definition2.version
                )
            )
            system[key] = str(value2)

        else:
            system[key] = str(value1 or value2)

    return system


def combine_environment(definition1, definition2):
    """Return combined environment from *definition1* and *definition2*.

    *definition1* and *definition2* must be valid
    :class:`~wiz.definition.Definition` instances.

    Each variable name from both definition's "environ" mappings will be
    gathered so that a final value can be set. If the a variable is only
    contained in one of the "environ" mapping, its value will be kept in the
    combined environment.

    If the variable exists in both "environ" mappings, the value from
    *definition2* must reference the variable name for the value from
    *definition1* to be included in the combined environment::

        >>> combine_environment(
        ...     Definition({"environ": {"key": "value2"})
        ...     Definition({"environ": {"key": "value1:${key}"}})
        ... )

        {"key": "value1:value2"}

    Otherwise the value from *definition2* will override the value from
    *definition1*::

        >>> combine_environment(
        ...     Definition({"environ": {"key": "value2"})
        ...     Definition({"environ": {"key": "value1"}})
        ... )

        {"key": "value1"}

    If other variables from *definition1* are referenced in the value fetched
    from *definition2*, they will be replaced as well::

        >>> combine_environment(
        ...     Definition({
        ...         "environ": {
        ...             "PLUGIN_PATH": "/path/to/settings",
        ...             "HOME": "/usr/people/me"
        ...        }
        ...     }),
        ...     Definition({
        ...         "environ": {
        ...             "PLUGIN_PATH": "${HOME}/.app:${PLUGIN_PATH}"
        ...         }
        ...     })
        ... )

        >>> combine_environment(
        ...    "PLUGIN_PATH",
        ...    {"PLUGIN_PATH": "${HOME}/.app:${PLUGIN_PATH}"},
        ...    {"PLUGIN_PATH": "/path/to/settings", "HOME": "/usr/people/me"}
        ... )

        {
            "HOME": "/usr/people/me",
            "PLUGIN_PATH": "/usr/people/me/.app:/path/to/settings"
        }

    .. warning::

        This process will stringify all variable values.

    """
    logger = mlog.Logger(__name__ + ".combine_environment")

    environ = {}

    environ1 = definition1.get("environ", {})
    environ2 = definition2.get("environ", {})

    for key in set(environ1.keys() + environ2.keys()):
        value1 = environ1.get(key)
        value2 = environ2.get(key)

        if value1 is not None and value2 is not None:
            if "${{{}}}".format(key) not in value2:
                logger.warning(
                    "The '{key}' variable is being overridden in "
                    "definition '{identifier}' [{version}]".format(
                        key=key,
                        identifier=definition2.identifier,
                        version=definition2.version
                    )
                )

            environ[key] = re.sub(
                "\${(\w+)}",
                lambda match: environ1.get(match.group(1)) or match.group(0),
                str(value2)
            )

        else:
            environ[key] = str(value1 or value2)

    return environ


def discover(paths, max_depth=None):
    """Discover and yield environment definitions found under *paths*.

    If *max_depth* is None, search all sub-trees under each path for
    environment files in JSON format. Otherwise, only search up to *max_depth*
    under each path. A *max_depth* of 0 should only search directly under the
    specified paths.

    """
    logger = mlog.Logger(__name__ + ".discover")

    for path in paths:
        # Ignore empty paths that could resolve to current directory.
        path = path.strip()
        if not path:
            logger.debug("Skipping empty path.")
            continue

        path = os.path.abspath(path)
        logger.debug(
            "Searching under {!r} for environment definition files."
            .format(path)
        )
        initial_depth = path.rstrip(os.sep).count(os.sep)
        for base, _, filenames in os.walk(path):
            depth = base.count(os.sep)
            if max_depth is not None and (depth - initial_depth) > max_depth:
                continue

            for filename in filenames:
                _, extension = os.path.splitext(filename)
                if extension != ".json":
                    continue

                definition_path = os.path.join(base, filename)
                logger.debug(
                    "Discovered environment definition file {!r}.".format(
                        definition_path
                    )
                )

                try:
                    definition = load(definition_path)
                except (
                    IOError, ValueError, TypeError,
                    InvalidRequirement, InvalidVersion
                ):
                    logger.warning(
                        "Error occurred trying to load environment definition "
                        "from {!r}".format(definition_path),
                        traceback=True
                    )
                    continue
                else:
                    logger.debug(
                        "Loaded environment definition {!r} from {!r}."
                        .format(definition.identifier, definition_path)
                    )
                    yield definition


def load(path):
    """Load and return :class:`Definition` from *path*."""
    with open(path, "r") as stream:
        definition_data = json.load(stream)

        # TODO: Validate with JSON-Schema.

        definition = Definition(**definition_data)
        definition["version"] = Version(definition.version)
        definition["requirement"] = map(
            Requirement, definition.get("requirement", [])
        )

        if "variant" in definition.keys():
            for variant_definition in definition["variant"]:
                variant_definition["requirement"] = map(
                    Requirement, variant_definition.get("requirement", [])
                )

        return definition


class Definition(collections.MutableMapping):
    """Environment Definition."""

    def __init__(self, *args, **kwargs):
        """Initialise environment definition."""
        super(Definition, self).__init__()
        self._mapping = {}
        self.update(*args, **kwargs)

    @property
    def identifier(self):
        """Return identifier."""
        return self.get("identifier", "unknown")

    @property
    def description(self):
        """Return name."""
        return self.get("description", "unknown")

    @property
    def version(self):
        """Return version."""
        return self.get("version", "unknown")

    def __str__(self):
        """Return string representation."""
        return "{}({!r}, {!r})".format(
            self.__class__.__name__, self.identifier, self._mapping
        )

    def __getitem__(self, key):
        """Return value for *key*."""
        return self._mapping[key]

    def __setitem__(self, key, value):
        """Set *value* for *key*."""
        self._mapping[key] = value

    def __delitem__(self, key):
        """Delete *key*."""
        del self._mapping[key]

    def __iter__(self):
        """Iterate over all keys."""
        for key in self._mapping:
            yield key

    def __len__(self):
        """Return count of keys."""
        return len(self._mapping)
