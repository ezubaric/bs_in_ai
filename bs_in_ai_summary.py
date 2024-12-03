import math
import random

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


def create_course_sequence(topological_sort, prerequisites, priorities, topics, courses):
    """
    Convert a sequence of topics into a sequence of courses.
    """

    non_prioritized = []
    for equivalence_set in topological_sort:
        non_prioritized += equivalence_set

    topics_added = set(['ROOT'])
    course_sequence = []
    
    candidates = [x for x in non_prioritized if x not in topics_added]
    while len(candidates) != 0:
        valid_topics = [x for x in priorities if x in candidates and set(prerequisites[x]) - topics_added == set()]

        if False:
            max_priority = max(priorities[x] for x in valid_courses)
            
            topic_to_add = [x for x in priorities if priorities[x] == max_priority][0]
        else:
            topic_to_add = candidates[0]

        print("Adding %s to course sequence, current: %s" % (topic_to_add, str(topics_added)))
        # Find out how many courses this topic has

        requirement = int(topics[topics['ID']==topic_to_add]['Requirement'].iloc[0])

        # Get those courses
        try:
            candidates = courses[courses["Skill"]==topic_to_add][courses["IncludeInSchedule"]=="YES"]
        except IndexError:
            # If we don't find flagged courses, take all of them
            candidates = courses[courses["Skill"]==topic_to_add]

        assert len(candidates) >= requirement, "Not enough courses (%i) to satisfy topic %s" % (requirement, topic_to_add)
        courses_to_add = list(candidates["Course"])
        if len(candidates) > requirement:
            courses_to_add = random.sample(courses_to_add, requirement)

        topics_added.add(topic_to_add)
        course_sequence += courses_to_add

        candidates = [x for x in non_prioritized if x not in topics_added]

    return course_sequence


def check_course_prereq(prereqs, history, concurrent):
    return True

def create_course_schedule(course_sequence, course_descriptions, courses_per_time=3):

    courses = defaultdict(list)

    for idx, course in enumerate(course_sequence):
        courses[idx // courses_per_time].append(course)

    history = []
    for time in courses:
        for course in courses[time]:
            prereqs = list(course_descriptions[course_descriptions["Course"]==course]["Prereqs"])
            assert len(prereqs) == 1, "Multiple entries for %s" % course
            prereqs = prereqs[0]
            
            assert check_course_prereq(prereqs, history, courses[time])
        history += courses[time]

    return courses


class Requirement:
    def __init__(self, key, name, concentration, requirement, courses, statuses):
        assert len(courses) == len(statuses)
        self.key = key
        self.name = name
        self.concentration = concentration
        self.requirement = requirement
        self.courses = [x.replace(" ", "~") for x in courses]
        self.statuses = statuses

    def render_latex(self):
        if self.requirement > 1:
            line =  "\\textbf{%s} (Take %i of the courses)" % (self.name, self.requirement)
        else:
            line = "\\textbf{%s}" % self.name

        courses = []
        for course, status in zip(self.courses, self.statuses):
            if status.lower() == "new":
                courses.append("\\textit{%s}" % course)
            else:
                courses.append(course)
        yield "%s & %s" % (line, ", ".join(courses))


def generate_latex_table(requirements, concentration, credit_per_course=3):
    credit_total = 0

    yield "\\rowcolors{2}{gray!25}{white}"
    yield "\\begin{longtable}{p{7cm}>{\\raggedleft\\arraybackslash}p{7cm}}"
    yield "Topic & Courses \\\\"
    yield "\\toprule"
    
    for requirement in requirements:
        if requirement.key == "ROOT":
            continue
        if requirement.concentration.lower() == "core" or requirement.concentration.lower() == concentration:
            credit_total = requirement.requirement * credit_per_course

        if requirement.concentration.lower() == concentration.lower():
            for latex in requirement.render_latex():
                padding = max(1, 75 - len(latex))
                yield latex + padding * " " + "\\\\"

    yield "\\bottomrule"

    yield "\\end{longtable}"

    if concentration == "core":
        yield "Total Credits: %i"% credit_total
    else:
        yield "Total Credits (including core): %i" % credit_total
            

def generate_requirements(raw_topics, raw_courses, topo):
    for group in topo:
        for topic in group:
            pretty = list(raw_topics[raw_topics["ID"] ==topic]["Pretty Label"])[0]
            requirements = list(raw_topics[raw_topics["ID"] ==topic]["Requirement"])[0] 
            concentration = list(raw_topics[raw_topics["ID"] ==topic]["Concentration"])[0]           
            courses = list(raw_courses[raw_courses["Skill"]==topic]["Course"])
            statuses = list(raw_courses[raw_courses["Skill"]==topic]["Status"])            
            yield Requirement(topic, pretty, concentration, requirements, courses, statuses)

def write_tables(raw_topics, raw_courses, topo):
    concentrations = set(raw_topics[raw_topics["Concentration"].notnull()].Concentration)

    # Always do Core first
    assert "Core" in concentrations
    concentrations.remove("Core")

    requirements = list(generate_requirements(raw_topics, raw_courses, topo))

    for concentration in ["Core"] + list(concentrations):
        with open("requirements/%s.tex" % concentration, 'w') as outfile:
            for line in generate_latex_table(requirements, concentration):
                outfile.write(line + "\n")

    

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
    with open("course_source/core.csv") as infile:
        raw_topics = pandas.read_csv(infile)

    with open("course_source/courses.csv") as infile:
        raw_courses = pandas.read_csv(infile)

    
    meta = dependency_graph_from_df(raw_topics)
    topo = extract_dependencies_and_sort(meta)

    prerequisites = {}
    for ii in meta:
        prerequisites[ii] = gather_prerequisites(meta, ii)

    print("Prerequisites", prerequisites)
    priorities = compute_priorities(prerequisites)

    print("Priorities", priorities)

    course_sequence = create_course_sequence(topo, prerequisites, priorities, raw_topics, raw_courses)
    print("Sequence", course_sequence)
    
    course_schedule = create_course_schedule(course_sequence, raw_courses)
    print("Schedule", course_schedule)

    create_graphviz(meta, output="dependency_graph/all")
    
    write_tables(raw_topics, raw_courses, topo)
