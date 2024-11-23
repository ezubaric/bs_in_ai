import math
import pandas
from pandas import DataFrame
from toposort import toposort
from collections import defaultdict
from typing import Dict, Union, Iterable
import graphviz

def extract_dependencies_and_sort(graph: Dict[str, Union[str, Iterable[str]]]) -> Iterable[Iterable[str]]:
    temp_graph = {}

    for ii in graph:
        temp_graph[ii] = graph[ii]["Dependencies"]

    result = list(toposort(temp_graph))
    result[0] = set(['ROOT'])
    return result

def create_graphviz(meta: Dict[str, Iterable[str]], name='', output='', concentrations=['core']):
    dot = graphviz.Digraph(comment=name)

    needed_nodes = []
    for node in meta:
        if meta[node]["Concentration"] in concentrations:
            needed_nodes.append(node)

        for requirements in meta[node]['Dependencies']:
            needed_nodes.append(requirements)

    for node in meta:
        label = meta[node]['Pretty Label']
        
        assert isinstance(label, str), "Bad label for %s: %s" % (node, label)
        dot.node(node, label)

        for parent in meta[node]['Dependencies']:
            dot.edge(parent, node)

    print(dot.source)
    dot.render(output)


def gather_prerequisites(all_requirements, concept):
    if concept == "ROOT":
        return set()
    else:
        result = set()
        for depdendency in all_requirements[concept]['Dependencies']:
            if depdendency != "ROOT":
                result.add(depdendency)
                result = result | gather_prerequisites(all_requirements, depdendency)
        return result

def compute_priorities(requirements):

    priority = defaultdict(int)

    for course in requirements:
        for prereq in requirements[course]:
            priority[prereq] += 1

    return priority

def create_schedule(topological_sort, prerequisites, priorities, course_descriptions, courses_per_time=3):

    non_prioritized = []
    for equivalence_set in topological_sort:
        non_prioritized += equivalence_set

    courses = defaultdict(list)
    added = set()

    time = 1
    for time in range(8):
        while len(courses[time]) < courses_per_time:
            candidates = [x for x in non_prioritized if x not in added]
            print(time, candidates)

            if len(candidates) == 0:
                break

            valid_courses = [x for x in priorities if x in candidates and set(prerequisites[x]) - added == set()]

            if False:
                max_priority = max(priorities[x] for x in valid_courses)
            
                course_to_add = [x for x in priorities if priorities[x] == max_priority][0]
            else:
                
                course_to_add = candidates[0]

            courses[time] += [course_to_add]
            added.add(course_to_add)
            
        courses[time]

    return courses





def dependency_graph_from_df(courses_df: DataFrame, graph: Dict[str, Dict[str, Iterable[str]]] = defaultdict(dict)) -> Dict[str, Dict[str, Iterable[str]]]:
    all_nodes = set(courses_df["ID"])

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
    file = "core"
    with open("course_source/%s.csv" % file) as infile:
        raw = pandas.read_csv(infile)
        meta = dependency_graph_from_df(raw)
        topo = extract_dependencies_and_sort(meta)

        prerequisites = {}
        for ii in meta:
            prerequisites[ii] = gather_prerequisites(meta, ii)

        print("Prerequisites", prerequisites)
        priorities = compute_priorities(prerequisites)

        print("Priorities", priorities)

        schedule = create_schedule(topo, prerequisites, priorities, meta)
        print("Schedule", schedule)

        create_graphviz(meta, output=file)
    
