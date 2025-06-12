"""
Entrypoint for `zog`.

Copyright (C) 2025 Nicholas M. Synovic.

"""

from pyzotero.zotero import Zotero
from networkx import DiGraph
import networkx as nx
from collections import defaultdict
from argparse import ArgumentParser, Namespace
from pathlib import Path


def cli() -> Namespace:
    """
    Parse command-line arguments for the Zotero knowledge graph tool.

    This CLI accepts arguments for accessing a Zotero library (either remote
    via API or local), selecting a collection within that library, and
    specifying an output location for the generated GraphML file.

    Supported options:
    - --library-id: Required Zotero library ID.
    - --library-type: Type of library ("user" or "group"). Defaults to "user".
    - --api-key: Zotero API key. Required unless using the --local flag.
    - --local: Use local access instead of API. Overrides the need for --api-key.
    - --collection-path: Path to the Zotero collection (e.g., "Projects/MyProject/Data").
    - --output-path: File path to output the GraphML data.

    Returns:
        Namespace: Parsed command-line arguments.

    """
    parser = ArgumentParser(
        prog="zog",
        description="ZOtero knowledge Graph.",
        epilog="Copyright (C) 2025 Nicholas M. Synovic.",
    )

    parser.add_argument(
        "--library-id",
        type=str,
        required=True,
        help="The Zotero library ID",
    )

    parser.add_argument(
        "--library-type",
        type=str,
        choices=["user", "group"],
        default="user",
        help="The type of Zotero library: 'user' or 'group' (default: user)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Zotero API key (required if not using --local)",
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local access (include this flag to enable it)",
    )

    parser.add_argument(
        "--collection-path",
        type=str,
        required=True,
        help="Path to the Zotero collection, e.g., 'Projects/PRIME VFV/Datasets'",
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        required=True,
        help="Path to write the output GraphML file, e.g., './output/graph.graphml'",
    )

    args = parser.parse_args()

    if not args.local and not args.api_key:
        parser.error(
            "The --api-key argument is required unless --local is specified."
        )

    return args


def get_named_collection_key(collections: list[dict], name: str) -> str:
    """
    Retrieve the key of a Zotero collection by its name.

    Iterates over a list of Zotero collection dictionaries to find a collection
    with a matching name and returns its associated key.

    Args:
        collections (list[dict]): List of Zotero collection objects, where each
            object is expected to have a "data" field containing a "name" key.
        name (str): The name of the collection to search for.

    Returns:
        str: The unique key of the matching Zotero collection.

    Raises:
        KeyError: If no collection with the specified name is found.

    """
    for collection in collections:
        collection_data: dict = collection["data"]
        if collection_data["name"] == name:
            return collection["key"]

    raise KeyError(f"{name} is not a Zotero collection")


def get_collection_key_from_path(
    collections: list[dict],
    collection_path: str,
) -> str:
    """
    Retrieve the key of a Zotero collection from a hierarchical path.

    Parses a collection path string (e.g., "Projects/Research/Data") and iteratively
    resolves each level using `get_named_collection_key`. Assumes that each path
    component corresponds to a collection name and that the final key corresponds to
    the last collection in the path.

    Note: This implementation assumes a flat collection list and does not verify
    parent-child relationships between collections.

    Args:
        collections (list[dict]): List of Zotero collection objects, where each
            object is expected to have a "data" field with a "name" key.
        collection_path (str): Slash-separated path to the desired collection.

    Returns:
        str: The key corresponding to the final collection in the path.

    Raises:
        KeyError: If any part of the path does not match a collection name.

    """
    key: str = ""
    split_collection_path: list[str] = collection_path.split(sep="/")

    path_part: str
    for path_part in split_collection_path:
        key = get_named_collection_key(
            collections=collections,
            name=path_part,
        )

    return key


def create_relationships(items: list[dict]) -> list[tuple[str, str | None]]:
    """
    Create relationships between Zotero items based on their metadata.

    For each item, this function attempts to extract related item keys from the
    'relations' field. If no 'dc:relation' field is present, a self-relationship
    is added (i.e., the item relates to itself).

    Args:
        items (list[dict]): A list of Zotero items. Each item is expected to contain
            a "data" field with a "key" and optionally a "relations" -> "dc:relation"
            list of related item URIs.

    Returns:
        list[tuple[str, str | None]]: A list of tuples representing
            relationships, where the first element is the source item's key and
            the second is the related item's key (or the same key if no relation
            is defined).

    """
    data: list[tuple[str, str | None]] = []

    item: dict
    for item in items:
        item_data: dict = item["data"]
        item_key: str = item_data["key"]

        try:
            item_relations: dict[str, list[str]] = item_data["relations"][
                "dc:relation"
            ]
        except KeyError:
            data.append((item_key, item_key))
            continue

        item_relation: str
        for item_relation in item_relations:
            relation_key: str = item_relation.split("/")[-1]
            data.append((item_key, relation_key))

    return data


def extract_nodes_from_relationships(
    relationships: list[tuple[str, str]],
) -> set[str]:
    """
    Extract unique node identifiers from a list of relationships.

    This function takes a list of (source, target) relationship tuples and
    returns a set of all unique node keys found in the relationships.

    Args:
        relationships (list[tuple[str, str]]): A list of tuples representing
            edges between nodes, where each tuple contains a source and target
            node key.

    Returns:
        set[str]: A set of unique node keys appearing in the relationships.

    """
    data: set[str] = set()

    relationship: tuple[str, str]
    for relationship in relationships:
        data.add(relationship[0])
        data.add(relationship[1])

    return data


def get_node_data(zotero: Zotero, nodes: set[str]) -> list[tuple[str, dict]]:
    data: list[tuple[str, dict]] = []

    node: str
    for node in nodes:
        datum: dict = {"item_type": "null", "title": "null", "url": "null"}
        item: dict = defaultdict(lambda: "note", zotero.item(node)["data"])

        datum["title"] = item["title"]
        datum["item_type"] = item["itemType"]
        datum["url"] = item["url"]

        data.append((node, datum))

    return data


def main() -> None:
    args: Namespace = cli()

    graph: DiGraph = DiGraph()

    zotero: Zotero = Zotero(
        library_id=args.library_id,
        library_type=args.library_type,
        api_key=args.api_key,
        local=args.local,
    )
    zotero_collections: list[dict] = zotero.collections()

    sub_collection_key: str = get_collection_key_from_path(
        collections=zotero_collections,
        collection_path=args.collection_path,
    )
    sub_collection_items: list[dict] = zotero.collection_items(
        sub_collection_key
    )

    graph_relationships: list[tuple[str, str]] = create_relationships(
        items=sub_collection_items
    )
    graph_nodes: set[str] = extract_nodes_from_relationships(
        relationships=graph_relationships
    )
    graph_nodes_with_data: list[tuple[str, dict]] = get_node_data(
        zotero=zotero, nodes=graph_nodes
    )

    graph.add_nodes_from(nodes_for_adding=graph_nodes_with_data)
    graph.add_edges_from(ebunch_to_add=graph_relationships)

    nx.write_graphml(graph, args.output_path.resolve(), prettyprint=True)


if __name__ == "__main__":
    main()
