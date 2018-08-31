# :coding: utf-8

"""Common symbols."""

#: Separator between the normal arguments and the command to run.
COMMAND_SEPARATOR = "--"

#: Default value when a definition value is unknown.
UNKNOWN_VALUE = "unknown"

#: Package request type.
PACKAGE_REQUEST_TYPE = "package"

#: Command request type.
COMMAND_REQUEST_TYPE = "command"

#: Identifier for packages which should be use implicitly in context.
IMPLICIT_PACKAGE = "implicit-packages"

#: History action for system identification.
SYSTEM_IDENTIFICATION_ACTION = "IDENTIFY_SYSTEM"

#: History action for definitions collection.
DEFINITIONS_COLLECTION_ACTION = "FETCH_DEFINITIONS"

#: History action for graph generation.
GRAPH_GENERATE_ACTION = "GENERATE_GRAPH"

#: History action for graph update.
GRAPH_UPDATE_ACTION = "UPDATE_GRAPH"

#: History action for computation of graph distance mapping.
GRAPH_DISTANCE_COMPUTATION_ACTION = "CREATE_DISTANCE_MAPPING"

#: History action for node creation within graph.
GRAPH_NODE_CREATION_ACTION = "CREATE_NODE"

#: History action for node removal within graph.
GRAPH_NODE_REMOVAL_ACTION = "REMOVE_NODE"

#: History action for link creation within graph.
GRAPH_LINK_CREATION_ACTION = "CREATE_LINK"

#: History action for version conflicts identification within graph.
GRAPH_VERSION_CONFLICTS_IDENTIFICATION_ACTION = "IDENTIFY_VERSION_CONFLICTS"

#: History action for variants conflicts identification within graph.
GRAPH_VARIANT_CONFLICTS_IDENTIFICATION_ACTION = "IDENTIFY_VARIANT_CONFLICTS"

#: History action for resolution error within graph.
GRAPH_RESOLUTION_FAILURE_ACTION = "RESOLUTION_ERROR"

#: History action for package extraction from graph.
GRAPH_PACKAGES_EXTRACTION_ACTION = "EXTRACT_PACKAGES"

#: History action for context extraction packages list.
CONTEXT_EXTRACTION_ACTION = "EXTRACT_CONTEXT"

#: History action for exception raised.
EXCEPTION_RAISE_ACTION = "RAISE_EXCEPTION"
