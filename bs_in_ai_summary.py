import math
import pandas
from pandas import DataFrame
from toposort import toposort
from collections import defaultdict
from typing import Dict, Union, Iterable
import graphviz

def extract_dependencies_and_sort(graph: Dict[str, Union[str, Iterable[str]]]) -> Dict[str, Iterable[str]]:
    temp_graph = {}

    for ii in graph:
        temp_graph[ii] = graph[ii]["Dependencies"]

    result = list(toposort(temp_graph))
    result[0] = set(['ROOT'])
    return result

def create_graphviz(meta: Dict[str, Iterable[str]], name='', output=''):
    dot = graphviz.Digraph(comment=name)

    for node in meta:
        label = meta[node]['Pretty Label']
        
        assert isinstance(label, str), "Bad label for %s: %s" % (node, label)
        dot.node(node, label)

        for parent in meta[node]['Dependencies']:
            dot.edge(parent, node)

    print(dot.source)
    dot.render(output)
                           

def dependency_graph_from_df(courses_df: DataFrame) -> Dict[str, Union[str, Iterable[str]]]:
    all_nodes = set(courses_df["ID"])

    graph = defaultdict(defaultdict)

    for values in [values for row, values in courses_df.iterrows() if values["ID"]]:
        id = values["ID"]

        if str(id) == "nan":
            continue

        print("Adding course %s" % id)

        graph[id] = values
        if isinstance(values["Dependencies"], float):
            graph[id]["Dependencies"] = {}
        else:
            dependencies = values["Dependencies"].split(",")
            if isinstance(dependencies, str):
                dependencies = [dependencies]
            assert all(x in all_nodes for x in dependencies), "Missing dependency: %s" % ":".join(x for x in dependencies if x not in all_nodes)
            graph[id]["Dependencies"] = dependencies
    
    return graph

if __name__ == "__main__":
    for file in ['core']:
        with open("%s.csv" % file) as infile:
            raw = pandas.read_csv(infile)
            meta = dependency_graph_from_df(raw)
            topo = extract_dependencies_and_sort(meta)
            create_graphviz(meta, output=file)
    
