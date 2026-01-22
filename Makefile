.PHONY: all dashboard velocity report epics gantt pdf clean help

# Default target - generate everything in one pass
all:
	@echo "Generating all planning outputs..."
	@cd bin && ../venv/bin/python generate_all.py

# Main dashboard (includes velocity and epic data)
dashboard:
	@echo "Generating comprehensive dashboard..."
	@cd bin && ../venv/bin/python generate_dashboard.py
	@echo "✓ Dashboard ready: public/*.html"

# Velocity chart only
velocity:
	@echo "Generating velocity chart..."
	@cd bin && ../venv/bin/python plot_velocity.py
	@echo "✓ Chart ready: public/*_velocity_chart.png"

# Excel report
report:
	@echo "Generating Excel report..."
	@cd bin && ../venv/bin/python generate_report.py
	@echo "✓ Report ready: public/*_planning_report_*.xlsx"

# Epic listing (console output)
epics:
	@echo "Listing epic remaining work..."
	@cd bin && ../venv/bin/python list_epic_work.py

# Gantt chart
gantt:
	@echo "Generating Gantt chart..."
	@cd bin && ../venv/bin/python generate_gantt.py
	@echo "✓ Gantt chart ready: public/*_gantt.png"

# PDF reports
pdf:
	@echo "Generating PDF reports..."
	@cd bin && ../venv/bin/python generate_pdf.py
	@echo "✓ PDF reports ready: public/*.pdf"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -f public/*.html public/*.png public/*.xlsx public/*.json public/*.pdf
	@echo "✓ Cleaned public/ directory"

# Show help
help:
	@echo "Jira Planning Tools - Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make              Generate dashboard, Gantt chart, and PDF (default)"
	@echo "  make dashboard    Generate HTML dashboard"
	@echo "  make gantt        Generate Gantt chart PNG"
	@echo "  make pdf          Generate PDF reports"
	@echo "  make velocity     Generate velocity chart PNG"
	@echo "  make report       Generate Excel report"
	@echo "  make epics        List epic remaining work (console)"
	@echo "  make clean        Remove all generated files"
	@echo "  make help         Show this help message"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Virtual environment activated (source venv/bin/activate)"
	@echo "  - .env file configured with Jira credentials"
	@echo ""
	@echo "Output directory: public/"
