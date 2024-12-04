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

    course_sequence = defaultdict(list)
    
    for step, equivalence_set in enumerate(topological_sort):
        for topic_to_add in equivalence_set:
            # Find out how many courses this topic has
            if topic_to_add == "ROOT":
                continue
            
            requirement = int(topics[topics['ID']==topic_to_add]['Requirement'].iloc[0])
            credits = int(topics[topics['ID']==topic_to_add]['Credits'].iloc[0])        

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

            course_sequence[step] += [(x, credits) for x in courses_to_add]

    return course_sequence


def check_course_prereq(prereqs, history, concurrent):
    return True

def create_course_schedule(course_sequence, course_descriptions, credits_per_time=11):
    courses = defaultdict(list)

    # Keep track of all courses added
    added = set()

    idx = 0
    current_credits = 0
    # This could be more efficient packing
    for step in course_sequence:
        for _ in course_sequence[step]:
            valid_courses = [(credits, course) for course, credits in course_sequence[step]
                             if current_credits + credits <= credits_per_time and
                             course not in added]
            valid_courses.sort()
            
            # Add the smallest unit course
            if not valid_courses:
                idx += 1
                current_credits = 0
                valid_courses = [(credits, course) for course, credits in course_sequence[step]
                                 if current_credits + credits <= credits_per_time and
                                 course not in added]
                valid_courses.sort()

            assert valid_courses, (course_sequence[step], courses, idx, current_credits)
            credits, course = valid_courses[0]
            courses[idx].append((course, credits, step))
            added.add(course)
            current_credits += credits
        idx += 1
        current_credits = 0

    history = []
    for time in courses:
        for course, credits, step in courses[time]:
            prereqs = list(course_descriptions[course_descriptions["Course"]==course]["Prereqs"])
            assert len(prereqs) == 1, "Multiple entries for %s" % course
            prereqs = prereqs[0]
            
            assert check_course_prereq(prereqs, history, courses[time])
        history += [x[0] for x in courses[time]]

    return courses


class Requirement:
    def __init__(self, key, name, concentration, requirement, courses, statuses, credit=3):
        assert len(courses) == len(statuses)
        self.key = key
        self.name = name
        self.concentration = concentration
        self.requirement = requirement
        self.credit = credit
        self.courses = [x.replace(" ", "~") for x in courses]
        self.statuses = statuses

    def render_latex(self):
        if self.requirement > 1:
            line =  "\\textbf{%s} [%i Credits Total] (Take %i of the courses)" % (self.name, self.requirement * self.credit, self.requirement)
        else:
            line = "\\textbf{%s} [%i Credits]" % (self.name, self.credit)

        courses = []
        for course, status in zip(self.courses, self.statuses):
            if status.lower() == "new":
                courses.append("\\textit{%s}" % course)
            else:
                courses.append(course)


        
        if len(courses) == 2:
            course_list = " or ".join(courses)
        elif len(courses) > 2:
            course_list = ", ".join(courses[:-1]) + ", or " + courses[-1]
        else:
            course_list = ", ".join(courses)
            
        yield "%s & %s" % (line, course_list)


def generate_latex_table(requirements, concentration):
    credit_total = 0

    yield "\\rowcolors{2}{gray!25}{white}"
    yield "\\begin{longtable}{p{7cm}>{\\raggedleft\\arraybackslash}p{7cm}}"
    yield "Topic & Courses \\\\"
    yield "\\toprule"
    
    for requirement in requirements:
        if requirement.key == "ROOT":
            continue
        if requirement.concentration.lower() == "core" or requirement.concentration.lower() == concentration.lower():
            credit_total += requirement.requirement * requirement.credit
        else:
            print("Excluding %s from %s" % (requirement.key, concentration))

        if requirement.concentration.lower() == concentration.lower():
            for latex in requirement.render_latex():
                padding = max(1, 75 - len(latex))
                yield latex + padding * " " + "\\\\"

    yield "\\bottomrule"

    yield "\\end{longtable}"

    if concentration.lower() == "core":
        yield "Total Credits for Core: %i"% credit_total
    else:
        yield "Total Credits (including core): %i" % credit_total
            

def generate_requirements(raw_topics, raw_courses, topo):
    for group in topo:
        for topic in group:
            pretty = list(raw_topics[raw_topics["ID"] ==topic]["Pretty Label"])[0]
            requirements = list(raw_topics[raw_topics["ID"] ==topic]["Requirement"])[0]
            credit = list(raw_topics[raw_topics["ID"] ==topic]["Credits"])[0]             
            concentration = list(raw_topics[raw_topics["ID"] ==topic]["Concentration"])[0]           
            courses = list(raw_courses[raw_courses["Skill"]==topic]["Course"])
            statuses = list(raw_courses[raw_courses["Skill"]==topic]["Status"])            
            yield Requirement(topic, pretty, concentration, requirements, courses, statuses, credit)

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

def latex_format_course(values, remove_empty_description=False):
    description = values["Description"]

    value = "\\item \\textbf{%s (%s)}" % (values["Title"], values["Course"])
    if description and not isinstance(description, float):
        return value + ": " + description
    elif not remove_empty_description:
        return value + "Description TBD"
    
    
def generate_readable_courses_given_status(raw_courses, status):
    yield "\\begin{enumerate}"
    for row, values in raw_courses[raw_courses["Status"]==status].iterrows():
        formatted = latex_format_course(values)
        if formatted:
            yield formatted
    yield "\\end{enumerate}"

def generate_readable_courses(raw_courses):
    statuses = set(raw_courses["Status"])

    for status in statuses:
        with open("course_descriptions/%s.tex" % status, 'w') as outfile:
            lines = "\n".join(generate_readable_courses_given_status(raw_courses, status))
            outfile.write(lines)

def write_schedule(schedule, filename):
    lines = []
    lines.append("\\begin{tabular}{cll}")
    lines.append("\\toprule")    
    lines.append("Year & Fall & Spring \\\\")
    lines.append("\\midrule")
    for year in range(4):
        year_string = str(year + 1)
        fall_courses = schedule[2 * year]
        spring_courses = schedule[2 * year + 1]

        for row in range(max(len(fall_courses), len(spring_courses))):
            if row < len(spring_courses):
                spring = "%s (%i) [%i]" % spring_courses[row]
            else:
                spring = ""

            if row < len(fall_courses):
                fall = "%s (%i) [%i]" % fall_courses[row]
            else:
                fall = ""
            lines.append("%s & %s & %s \\\\" % (year_string, fall, spring))
            year_string = ""
        if year != 3:
            lines.append("\\midrule")
        else:
            lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    
    with open(filename, 'w') as outfile:
        outfile.write("\n".join(lines))
            
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

    for specialization in ["GenAI"]:
        course_sequence = create_course_sequence(topo, prerequisites, priorities, raw_topics, raw_courses)
        print("Sequence (%s)" % specialization, course_sequence)
    
        course_schedule = create_course_schedule(course_sequence, raw_courses)
        print("Schedule (%s)" % specialization, course_schedule)

        write_schedule(course_schedule, "schedules/%s.tex" % specialization)

    create_graphviz(meta, output="dependency_graph/all")
    
    write_tables(raw_topics, raw_courses, topo)

    generate_readable_courses(raw_courses)
