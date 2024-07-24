import tkinter as tk
from tkinter import messagebox, filedialog, Toplevel, Menu
from tkcalendar import Calendar
import time
from threading import Thread, Event
import json
import os
import sys
from datetime import datetime
from pydub import AudioSegment
from pydub.playback import play
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

timer_thread = None
timer_event = None
pause_event = None
version = "3.2.8 Build 38"
config_file = "timers_config.json"
log_file = "task_logs.json"
tasks = {}
task_logs = {}

root = tk.Tk()
root.title("Task Timer")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

start_icon = tk.PhotoImage(file=resource_path("icons/start.png"))
pause_icon = tk.PhotoImage(file=resource_path("icons/pause.png"))
resume_icon = tk.PhotoImage(file=resource_path("icons/resume.png"))
stop_icon = tk.PhotoImage(file=resource_path("icons/stop.png"))
add_icon = tk.PhotoImage(file=resource_path("icons/add.png"))
edit_icon = tk.PhotoImage(file=resource_path("icons/edit.png"))
delete_icon = tk.PhotoImage(file=resource_path("icons/delete.png"))
move_up_icon = tk.PhotoImage(file=resource_path("icons/up.png"))
move_down_icon = tk.PhotoImage(file=resource_path("icons/down.png"))

def play_sound(sound_file):
    sound = AudioSegment.from_file(sound_file, format="wav")
    play(sound)

def log_task(task, duration):
    date_str = datetime.now().strftime("%Y-%m-%d")
    if date_str not in task_logs:
        task_logs[date_str] = []
    task_logs[date_str].append({"task": task, "duration": duration})
    with open(log_file, 'w') as file:
        json.dump(task_logs, file)
    if 'chart_window' in globals() and chart_window.winfo_exists():
        update_pie_chart(date_str, chart_window.frame_pie_chart)

def load_task_logs():
    global task_logs
    if os.path.exists(log_file):
        with open(log_file, 'r') as file:
            task_logs = json.load(file)
    else:
        task_logs = {}

def countdown_timer(duration, sound_file, event, pause_event, task):
    start_time = datetime.now()
    while duration >= 0 and not event.is_set():
        if not pause_event.is_set():
            mins, secs = divmod(duration, 60)
            timeformat = '{:02d}:{:02d}'.format(mins, secs)
            timer_display_label.config(text=timeformat)
            time.sleep(1)
            duration -= 1
        else:
            time.sleep(1)
    if not event.is_set():
        play_sound(sound_file)
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds() / 60
        log_task(task, elapsed_time)
        clear_timer()
        timer_display_label.config(text="")

def set_timer(task):
    global timer_thread, timer_event, pause_event
    if timer_thread and timer_thread.is_alive():
        messagebox.showwarning("Timer Running", "A timer is already running. Please stop it before starting a new one.")
        return

    duration = tasks[task]['duration'] * 60
    sound_file = tasks[task]['sound']
    timer_display_label.config(text="")
    timer_event = Event()
    pause_event = Event()
    timer_thread = Thread(target=countdown_timer, args=(duration, sound_file, timer_event, pause_event, task))
    timer_thread.start()
    start_pause_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.NORMAL)
    start_pause_button.config(image=pause_icon, command=pause_timer)

def pause_timer():
    global pause_event
    pause_event.set()
    start_pause_button.config(image=resume_icon, command=resume_timer)

def resume_timer():
    global pause_event
    pause_event.clear()
    start_pause_button.config(image=pause_icon, command=pause_timer)

def stop_timer():
    global timer_thread, timer_event
    if timer_thread and timer_thread.is_alive():
        timer_event.set()
        timer_thread.join()
    clear_timer()
    timer_display_label.config(text="")

def choose_sound(entry):
    sound_file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if sound_file:
        entry.delete(0, tk.END)
        entry.insert(0, sound_file)

def clear_timer():
    timer_display_label.config(text="")
    start_pause_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.DISABLED)

def save_tasks():
    with open(config_file, 'w') as file:
        json.dump(tasks, file)

def load_tasks():
    global tasks
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            tasks = json.load(file)
    else:
        tasks = {}

def init_tasks():
    for task in tasks:
        listbox_tasks.insert(tk.END, task)

def add_task_window():
    add_window = Toplevel(root)
    add_window.title("Add Task")
    add_window.attributes("-topmost", True)

    tk.Label(add_window, text="Task").grid(row=0, column=0)
    entry_task_add = tk.Entry(add_window)
    entry_task_add.grid(row=0, column=1)

    tk.Label(add_window, text="Duration (minutes)").grid(row=1, column=0)
    entry_duration_add = tk.Entry(add_window)
    entry_duration_add.grid(row=1, column=1)

    tk.Label(add_window, text="Sound File").grid(row=2, column=0)
    entry_sound_add = tk.Entry(add_window)
    entry_sound_add.grid(row=2, column=1)
    tk.Button(add_window, text="Choose Sound", command=lambda: choose_sound(entry_sound_add)).grid(row=2, column=2)

    def save_new_task():
        task = entry_task_add.get()
        try:
            duration = int(entry_duration_add.get())
            sound_file = entry_sound_add.get()
            if task in tasks:
                messagebox.showerror("Duplicate Task", "This task name already exists. Please choose a different name.")
            elif task and duration and sound_file:
                tasks[task] = {'duration': duration, 'sound': sound_file}
                listbox_tasks.insert(tk.END, task)
                save_tasks()
                add_window.destroy()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid number for the duration.")

    tk.Button(add_window, text="Save", command=save_new_task).grid(row=3, columnspan=3)

def edit_task():
    try:
        selected_task = listbox_tasks.get(listbox_tasks.curselection())
        edit_window = Toplevel(root)
        edit_window.title("Edit Task")
        edit_window.attributes("-topmost", True)

        tk.Label(edit_window, text="Task").grid(row=0, column=0)
        entry_task_edit = tk.Entry(edit_window)
        entry_task_edit.grid(row=0, column=1)
        entry_task_edit.insert(0, selected_task)

        tk.Label(edit_window, text="Duration (minutes)").grid(row=1, column=0)
        entry_duration_edit = tk.Entry(edit_window)
        entry_duration_edit.grid(row=1, column=1)
        entry_duration_edit.insert(0, tasks[selected_task]['duration'])

        tk.Label(edit_window, text="Sound File").grid(row=2, column=0)
        entry_sound_edit = tk.Entry(edit_window)
        entry_sound_edit.grid(row=2, column=1)
        entry_sound_edit.insert(0, tasks[selected_task]['sound'])
        tk.Button(edit_window, text="Choose Sound", command=lambda: choose_sound(entry_sound_edit)).grid(row=2, column=2)

        def save_edits():
            new_task_name = entry_task_edit.get()
            try:
                new_duration = int(entry_duration_edit.get())
                new_sound_file = entry_sound_edit.get()
                if new_task_name != selected_task and new_task_name in tasks:
                    messagebox.showerror("Duplicate Task", "This task name already exists. Please choose a different name.")
                else:
                    if new_task_name != selected_task:
                        tasks.pop(selected_task)
                        listbox_tasks.delete(listbox_tasks.curselection())
                        listbox_tasks.insert(tk.END, new_task_name)
                    tasks[new_task_name] = {'duration': new_duration, 'sound': new_sound_file}
                    save_tasks()
                    edit_window.destroy()
            except ValueError:
                messagebox.showerror("Invalid input", "Please enter a valid number for the duration.")

        tk.Button(edit_window, text="Save", command=save_edits).grid(row=3, columnspan=3)

    except tk.TclError:
        messagebox.showerror("No Selection", "Please select a task to edit.")

def delete_task():
    try:
        selected_task = listbox_tasks.get(listbox_tasks.curselection())
        if messagebox.askyesno("Delete Task", f"Are you sure you want to delete the task '{selected_task}'?"):
            tasks.pop(selected_task)
            listbox_tasks.delete(listbox_tasks.curselection())
            save_tasks()
    except tk.TclError:
        messagebox.showerror("No Selection", "Please select a task to delete.")

def move_up():
    try:
        selected_index = listbox_tasks.curselection()[0]
        if selected_index > 0:
            task = listbox_tasks.get(selected_index)
            listbox_tasks.delete(selected_index)
            listbox_tasks.insert(selected_index - 1, task)
            listbox_tasks.selection_set(selected_index - 1)
            tasks_list = list(listbox_tasks.get(0, tk.END))
            update_tasks(tasks_list)
    except IndexError:
        messagebox.showerror("No Selection", "Please select a task to move up.")

def move_down():
    try:
        selected_index = listbox_tasks.curselection()[0]
        if selected_index < listbox_tasks.size() - 1:
            task = listbox_tasks.get(selected_index)
            listbox_tasks.delete(selected_index)
            listbox_tasks.insert(selected_index + 1, task)
            listbox_tasks.selection_set(selected_index + 1)
            tasks_list = list(listbox_tasks.get(0, tk.END))
            update_tasks(tasks_list)
    except IndexError:
        messagebox.showerror("No Selection", "Please select a task to move down.")

def update_tasks(tasks_list):
    global tasks
    updated_tasks = {task: tasks[task] for task in tasks_list}
    tasks = updated_tasks
    save_tasks()

def show_pie_chart_window():
    global chart_window
    chart_window = Toplevel(root)
    chart_window.title("Pie Chart")
    chart_window.attributes("-topmost", True)

    frame_calendar_pie = tk.Frame(chart_window)
    frame_calendar_pie.pack(pady=10)

    cal = Calendar(frame_calendar_pie, selectmode='day', date_pattern='yyyy-mm-dd')
    cal.pack(side=tk.LEFT, padx=10)
    chart_window.frame_pie_chart = tk.Frame(frame_calendar_pie)
    chart_window.frame_pie_chart.pack(side=tk.RIGHT, padx=10)

    def on_date_select(event):
        selected_date = cal.selection_get().strftime("%Y-%m-%d")
        update_pie_chart(selected_date, chart_window.frame_pie_chart)
        chart_window.update_idletasks()
        chart_window.geometry("")

    cal.bind("<<CalendarSelected>>", on_date_select)

def update_pie_chart(date, window):
    for widget in window.winfo_children():
        widget.destroy()

    if date in task_logs:
        tasks = task_logs[date]
        task_summary = {}
        for task in tasks:
            if task['task'] in task_summary:
                task_summary[task['task']] += task['duration']
            else:
                task_summary[task['task']] = task['duration']

        labels = list(task_summary.keys())
        sizes = list(task_summary.values())

        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct=lambda p: f'{p * sum(sizes) / 100:.1f} mins', startangle=90)
        ax.axis('equal')

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack()
    else:
        tk.Label(window, text="No Data Available", font=('Helvetica', 16)).pack()

def show_about():
    messagebox.showinfo("About Task Timer", f"Task Timer\nVersion: {version}\nDesigned by @phys-cpp")

load_tasks()
load_task_logs()

menu_bar = Menu(root)
root.config(menu=menu_bar)

chart_menu = Menu(menu_bar, tearoff=0)
chart_menu.add_command(label="View Chart", command=show_pie_chart_window)
menu_bar.add_cascade(label="Chart", menu=chart_menu)

help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="About Task Timer", command=show_about)
menu_bar.add_cascade(label="Help", menu=help_menu)

tk.Label(root, text="Tasks").pack()
frame_tasks = tk.Frame(root)
frame_tasks.pack()
listbox_tasks = tk.Listbox(frame_tasks, height=17)
listbox_tasks.grid(row=0, column=0, rowspan=5)
init_tasks()

def create_button_with_tooltip(frame, image, command, tooltip_text, row, column, padx=0, pady=0):
    button = tk.Button(frame, image=image, command=command)
    button.grid(row=row, column=column, padx=padx, pady=pady)
    def on_enter(event):
        tooltip_label.config(text=tooltip_text)
        x = event.widget.winfo_rootx() - root.winfo_rootx()
        y = event.widget.winfo_rooty() - root.winfo_rooty() - 30
        tooltip_label.place(x=x, y=y)
    def on_leave(event):
        tooltip_label.place_forget()
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    return button

tooltip_label = tk.Label(root, text="", bg="yellow", fg="black")

create_button_with_tooltip(frame_tasks, add_icon, add_task_window, "Add Task", 0, 1)
create_button_with_tooltip(frame_tasks, edit_icon, edit_task, "Edit Task", 1, 1)
create_button_with_tooltip(frame_tasks, move_up_icon, move_up, "Move Up", 2, 1)
create_button_with_tooltip(frame_tasks, move_down_icon, move_down, "Move Down", 3, 1)
create_button_with_tooltip(frame_tasks, delete_icon, delete_task, "Delete Task", 4, 1)

timer_buttons_frame = tk.Frame(root)
timer_buttons_frame.pack()

create_button_with_tooltip(timer_buttons_frame, start_icon, lambda: set_timer(listbox_tasks.get(tk.ACTIVE)), "Start Timer", 0, 0, padx=5, pady=5)
start_pause_button = create_button_with_tooltip(timer_buttons_frame, pause_icon, pause_timer, "Pause", 0, 1, padx=5, pady=5)
start_pause_button.config(state=tk.DISABLED)
stop_button = create_button_with_tooltip(timer_buttons_frame, stop_icon, stop_timer, "Stop", 0, 2, padx=5, pady=5)
stop_button.config(state=tk.DISABLED)

timer_display_label = tk.Label(root, text="", font=('Helvetica', 58))
timer_display_label.pack()

designed_by_label = tk.Label(root, text="Designed by @phys-cpp", font=('Helvetica', 10))
designed_by_label.pack(side=tk.BOTTOM, pady=0)

version_label = tk.Label(root, text=f"Version: {version}", font=('Helvetica', 10))
version_label.pack(side=tk.BOTTOM, pady=0)

root.mainloop()
