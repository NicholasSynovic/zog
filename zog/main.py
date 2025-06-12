from pyzotero.zotero import Zotero
from networkx import DiGraph
import networkx as nx
from typing import Any
from collections import defaultdict
import matplotlib.pyplot as plt
from argparse import ArgumentParser, Namespace
from pathlib import Path


def cli() -> Namespace:
    parser = ArgumentParser(
        prog="zog",
        description="ZOtero knowledge Graph.",
        epilog="Copyright (c) Nicholas Synovic, 2025",
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
    for collection in collections:
        collection_data: dict = collection["data"]
        if collection_data["name"] == name:
            return collection["key"]

    raise KeyError(f"{name} is not a Zotero collection")


def get_collection_key_from_path(
    collections: list[dict],
    collection_path: str,
) -> str:
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

    # library_id="6051933"
    # library_type="user"
    # api_key = ""
    # local=True
    # collection_path: str = "Projects/PRIME VFV/Datasets"

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
