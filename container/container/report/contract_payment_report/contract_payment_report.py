from container.reporting import execute_report


def execute(filters=None):
	return execute_report("Contract Payment Report", filters)
