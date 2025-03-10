import math
import random

import pandas
from pandas import DataFrame
from toposort import toposort
from collections import defaultdict
from typing import Dict, Union, Iterable
import graphviz

kHEADER = """
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% DO NOT EDIT THIS FILE, IT IS AUTOMATICALLY GENERATED
% INSTEAD, EDIT THE FILE HERE:
%
% https://docs.google.com/spreadsheets/d/1qRaEKxhyfwjHDWa3burGeqK0zeC00Br8NhJfnMWXJdk/edit?usp=sharing
%
% If you edit this file, your changes will be overwritten from this
% spreadsheet linked above.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
"""


def write_budget_tables(source_file, output_file, table_columns={'Total Students': "Total Students",
                                                                 'Num PTK': "\\abr{ptk} Faculty",
                                                                 'TTK': "\\abr{ttk} Faculty",
                                                                 'TA FTE': "\\abr{ta fte}",
                                                                 'Budget': "Total Expenditures"}):
    from csv import DictReader
    budget_constants = defaultdict(dict)
    with open(source_file, 'r') as infile:
        raw = DictReader(infile)
        for row in raw:
            val = row["Value"]
            if "$" in val:
                val = val.replace("$", "\\$")
            if row['Year']:
                year = int(row['Year'])
                budget_constants[row["Constant"]][str(year)] = val
            else:                
                budget_constants[row["Constant"]] = val

    
    header = "\\toprule" + "\t&".join(["\\textbf{Year}"] + list(table_columns.values()))
    header += "\\\\ \n \\midrule \n"
    lines = []
    for year in [str(x) for x in range(1, 6)]:
        lines.append(" &\t".join([year] + [budget_constants[x][year] for x in table_columns]))
    lines.append("\\bottomrule")
    
    with open(output_file, 'w') as outfile:
        for key in budget_constants:
            if key not in table_columns and key:
                outfile.write("\\newcommand{\\%s}[0]{%s}\n" % (key.replace(" ", ""), str(budget_constants[key])))
        outfile.write("\\begin{table}\n")
        outfile.write("\\begin{center}\n")
        outfile.write("\\begin{tabular}{lrrrrr}\n")
        outfile.write(header)
        outfile.write("\t\\\\ \n".join(lines))
        outfile.write("\n\\end{tabular}\n")
        outfile.write("\\end{center}\n")
        outfile.write("\\caption{Budget projections for the program.}\n")
        outfile.write("\\label{tab:budget}\n")
        outfile.write("\\end{table}\n")        
    return budget_constants
    

def extract_dependencies_and_sort(graph: Dict[str, Union[str, Iterable[str]]]) -> Iterable[Iterable[str]]:
    temp_graph = {}

    for ii in graph:
        temp_graph[ii] = graph[ii]["Dependencies"]

    result = list(toposort(temp_graph))
    result[0] = set(['ROOT'])
    return result

kCOLOR_LOOKUP={"AI": "lightyellow", "CS": "pink", "MATH": "lightgreen", "Outside": "lightskyblue"}

def lookup_color(skill_attributes):
    if isinstance(skill_attributes["Unit"], float):
        return 'gray90'

    for field in kCOLOR_LOOKUP:
        print(skill_attributes["Unit"])
        if skill_attributes["Unit"].startswith(field):
            return kCOLOR_LOOKUP[field]
    return 'gray90'

def create_graphviz(meta: Dict[str, Iterable[str]], name='', output='', concentrations=['core'], color_lookup=lookup_color):
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
        dot.node(node, label, fillcolor=color_lookup(meta[node]), style="filled")

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

            assert len(candidates) >= requirement, "Not enough courses (%i) to satisfy topic %s.  Have: %s" % (requirement, topic_to_add, " ".join(candidates["Course"]))
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
            # assert len(prereqs) == 1, "Multiple entries for %s" % course
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

        # If you have to take all the courses, say "and" here
        if len(self.courses) == self.requirement:
            join = "and"
        else:
            join = "or"
            
        courses = []
        for course, status in zip(self.courses, self.statuses):
            try:
                if status.lower() == "new":
                    courses.append("\\textit{%s}" % course)
                else:
                    courses.append(course)
            except AttributeError:
                print("Problem parsing %s" % str(course))

                
        if len(courses) == 2:
            conjunction = " %s " % join
            course_list = conjunction.join(courses)
        elif len(courses) > 2:
            conjunction = ", %s " % join
            course_list = ", ".join(courses[:-1]) + conjunction + courses[-1]
        else:
            course_list = ", ".join(courses)
            
        yield "%s & %s" % (line, course_list)


def generate_latex_table(requirements, concentration):
    credit_total = 0

    yield "\\rowcolors{2}{gray!25}{white}"
    yield "\\begin{longtable}{p{7cm}>{\\raggedleft\\arraybackslash}p{7cm}}"
    yield "Course Subject & Courses \\\\"
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
            outfile.write(kHEADER)            
            for line in generate_latex_table(requirements, concentration):
                outfile.write(line + "\n")
            if concentration != "Core":
                "Or other designated courses as approved by program administration."

    

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

def format_prereq_from_skills(prereq_to_print, skills, courses):
    
    prereqs = defaultdict(set)
    for prereq in prereq_to_print.split(","):
        prereqs[prereq]

    for prereq in prereqs:
        for course in courses[courses.Skill==prereq].Course:
            prereqs[prereq].add(course)

    prereq_string = []
    for prereq in prereqs:
        prereq_string.append(" OR ".join(prereqs[prereq]))

    return " AND ".join(prereq_string)

def latex_format_course(values, skills, courses, remove_empty_description=False):
    skill = values["Skill"]
    description = values["Description"]

    value = "\\item \\textbf{%s (%s)}" % (values["Title"], values["Course"])
    if description and not isinstance(description, float):
        value += ": " + description

    prereq_string = values["Prereqs"]

    # This can probably be refactored, but no time to do that right now
    if not isinstance(prereq_string, float):
        if "," in prereq_string:
            prereq_string = "(" + ") AND (".join(format_prereq_from_skills(x, skills, courses) for x in prereq_string.split(",")) + ")"
        else:
            prereq_string = format_prereq_from_skills(prereq_string, skills, courses)

    else:
        # Look up prereq from skills list instead
        
        if len(skills[skills.ID == skill].Dependencies) > 0:
            prereq_string = list(skills[skills.ID == skill].Dependencies)[0]
            if prereq_string == "ROOT":
                prereq_string = ""
            elif "and" in prereq_string.lower():
                prereq_string = prereq_string.upper()
            elif "," in prereq_string:
                # Removed the label because it was too much work to expand it
                prereq_string = "(" + ") AND (".join(format_prereq_from_skills(x, skills, courses) for x in prereq_string.split(",")) + ")"
                # prereq_string = "(" + ") AND (".join("%s: " % x + format_prereq_from_skills(x, skills, courses) for x in prereq_string.split(",")) + ")"
            else:
                prereq_string = format_prereq_from_skills(prereq_string, skills, courses)
        else:    
            prereq_string = ""

    if prereq_string != "" and "()" not in prereq_string:
        value += " Prereqs: %s" % prereq_string


    return value
    
    
def generate_readable_courses_given_status(raw_courses, status, skills):
    yield "\\begin{enumerate}"
    for row, values in raw_courses[raw_courses["Status"]==status].drop_duplicates(subset=['Course']).sort_values(by='Course').iterrows():
        formatted = latex_format_course(values, skills, raw_courses)
        if formatted:
            yield formatted
    yield "\\end{enumerate}"

def generate_readable_courses(raw_courses, skills):
    statuses = set(raw_courses["Status"])

    for status in statuses:
        with open("course_descriptions/%s.tex" % status, 'w') as outfile:
            outfile.write(kHEADER)
            lines = "\n".join(generate_readable_courses_given_status(raw_courses, status, skills))
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
        outfile.write(kHEADER)        
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

        # Generating error
        # course_schedule = create_course_schedule(course_sequence, raw_courses)
        # print("Schedule (%s)" % specialization, course_schedule)

        # write_schedule(course_schedule, "schedules/%s.tex" % specialization)

    create_graphviz(meta, output="dependency_graph/all")
    
    write_tables(raw_topics, raw_courses, topo)

    generate_readable_courses(raw_courses, raw_topics)

    write_budget_tables("course_source/budget.csv", "tables/budget.tex")
