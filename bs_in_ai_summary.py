
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
    result[0] = ('ROOT', [])
    return result

def create_graphviz(dependency: Dict[str, Iterable[str]], meta: Dict[str, Iterable[str]], name='', output=''):
    dot = graphviz.Digraph(comment=name)

    for node in dependency:
        dot.node(node, meta[node]['Label'])

        for parent in dependency[node]:
            dot.edges([node, parent])

    dot.write("%s.dot" % output)
    dot.render(output)
                           

def dependency_graph_from_df(courses_df: DataFrame) -> Dict[str, Union[str, Iterable[str]]]:
    all_nodes = set(courses_df["ID"])

    graph = defaultdict(defaultdict)

    for values in [values for row, values in courses_df.iterrows() if values["ID"]]:
        id = values["ID"]

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
            create_graphviz(topo, meta, output=file)
    
