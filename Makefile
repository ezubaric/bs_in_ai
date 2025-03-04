
copy_courses: 
	mv ~/Downloads/AI\ BS\ Courses\ -\ Skills.csv course_source/core.csv
	mv ~/Downloads/AI\ BS\ Courses\ -\ Courses.csv course_source/courses.csv
	mv ~/Downloads/AI\ BS\ Courses\ -\ Budget\ Assumptions.csv course_source/budget.csv

clean:
	rm course_descriptions/*
	rm requirements/*.tex
	rm dependency_graph/*
	rm main.pdf

main.pdf: course_source/core.csv course_source/courses.csv bs_in_ai_summary.py main.tex
	./venv/bin/python3 bs_in_ai_summary.py
	pdflatex los
	pdflatex main
	pdflatex main
	pdflatex qualifications
	latex2html -split 0 main.tex
	grep -h -v '25white' main/index.html > main/clean.html
