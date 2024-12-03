
clean:
	rm course_descriptions/*
	rm requirements/*.tex
	rm dependency_graph/*
	rm main.pdf

main.pdf: course_source/core.csv course_source/courses.csv bs_in_ai_summary.py main.tex
	./venv/bin/python3 bs_in_ai_summary.py
	pdflatex main
	pdflatex main
