import pyRTOS


def default_scheduler(tasks):
    messages = []
    running_task = None

    for task in tasks:

        if task.state == pyRTOS.READY:
            if running_task == None:
                running_task = task
        elif task.state == pyRTOS.BLOCKED:
            if True in map(lambda x: next(x), task.ready_conditions):
                task.state = pyRTOS.READY
                task.ready_conditions = []
                if running_task == None:
                    running_task = task
        elif task.state == pyRTOS.RUNNING:
            if (running_task == None) or (task.priority <= running_task.priority):
                running_task = task
            else:
                task.state = pyRTOS.READY

    if running_task:
        print(f"▶️ Running Task: {running_task.name}")  # Debugging
        running_task.state = pyRTOS.RUNNING
        try:
            messages = running_task.run_next()
        except StopIteration:
            print(f"⚠️ Task {running_task.name} Finished and Removed")  # Debugging
            tasks.remove(running_task)
    
    return messages

