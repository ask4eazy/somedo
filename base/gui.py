#!/usr/bin/env python3

from threading import Event, Thread
from functools import partial
from tkinter import Tk, Frame, LabelFrame, Label, Button, Checkbutton, Entry, Text, PhotoImage, StringVar, BooleanVar, IntVar
from tkinter import BOTH, GROOVE, END, W, E, X, LEFT, RIGHT
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from base.storage import Storage
from base.worker import Worker
from base.chrometools import Chrome

class GuiRoot(Tk):
	'Graphic user interface using Tkinter, main / root window'

	JOBLISTLENGTH = 10
	BUTTONWIDTH = 16
	BIGENTRY = 120
	PADX = 8
	PADY = 8

	def __init__(self, master):
		'Generate object for main / root window.'
		self.storage = Storage()	# object for file system accesss
		self.chrome = Chrome()	# object to work with chrome/chromium
		self.worker = Worker(self.storage, self.chrome)	# generate object for the worker (smd_worker.py)
		self.jobs = []	# start with empty list for the jobs
		master.title('Social Media Downloader')	# window title for somedo
		self.__set_icon__(master)	# give the window manager an application icon
		frame_jobs = LabelFrame(master, text='Jobs')	# in this tk-frame the jobs will be displayed
		frame_jobs.pack(fill=X, expand=True)	# tk-stuff
		self.tk_jobbuttons = []
		for i in range(self.JOBLISTLENGTH):
			frame_job = Frame(frame_jobs)
			frame_job.pack(fill=X, expand=True)
			self.tk_jobbuttons.append(StringVar(frame_job))
			Button(frame_job, textvariable=self.tk_jobbuttons[i], anchor=W,
				command=partial(self.__job_edit__, i)).pack(side=LEFT, fill=X, expand=True)
			Button(frame_job, text='\u2191', command=partial(self.__job_up__, i)).pack(side=LEFT)
			Button(frame_job, text='\u2193', command=partial(self.__job_down__, i)).pack(side=LEFT)
		frame_row = LabelFrame(master)
		frame_row.pack(fill=BOTH, expand=True)
		Button(frame_row, text="Start jobs", width=self.BUTTONWIDTH,
			command=self.__start_hidden__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		if self.worker.DEBUG:
			Button(frame_row, text="DEBUG: start visible", width=self.BUTTONWIDTH,
				command=self.__start__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		Button(frame_row, text="Stop running task", width=self.BUTTONWIDTH,
			command=self.__stop__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		Button(frame_row, text='Purge job list', width=self.BUTTONWIDTH,
			command=self.__purge_jobs__).pack(side=RIGHT, pady=self.PADY)
		frame_row = LabelFrame(master, text='Add Job')	# add job frame
		frame_row.pack(fill=BOTH, expand=True)
		for i in self.worker.MODULES:	# generate buttons for the modules
			Button(frame_row, text=i['name'], width=self.BUTTONWIDTH,
				command=partial(self.__new_job__, i['name'])).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		frame_config = LabelFrame(master, text='Configuration')
		frame_config.pack(fill=BOTH, expand=True)
		nb_config = ttk.Notebook(frame_config)	# here is the tk-notebook for the modules
		nb_config.pack(padx=self.PADX, pady=self.PADY)
		frame_nb = ttk.Frame(nb_config)
		nb_config.add(frame_nb, text='General')
		frame_row = Frame(frame_nb)
		frame_row.pack(fill=BOTH, expand=True)
		Label(frame_row, text='Output directory:', anchor=E, width=self.BUTTONWIDTH).pack(side=LEFT, padx=self.PADX)
		self.tk_outdir = StringVar(frame_row, self.storage.outdir)
		self.tk_outdir_entry = Entry(frame_row, textvariable=self.tk_outdir, width=self.BIGENTRY)
		self.tk_outdir_entry.pack(side=LEFT)
		Button(frame_row, text='\u261a', command=self.__output_dir__).pack(side=LEFT, padx=self.PADX)
		frame_row = Frame(frame_nb)
		frame_row.pack(fill=BOTH, expand=True)
		Label(frame_row, text='Chrome path:', anchor=E, width=self.BUTTONWIDTH).pack(side=LEFT, padx=self.PADX)
		self.tk_chrome = StringVar(frame_row, self.chrome.path)
		self.tk_chrome_entry = Entry(frame_row, textvariable=self.tk_chrome, width=self.BIGENTRY)
		self.tk_chrome_entry.pack(side=LEFT)
		Button(frame_row, text='\u261a', command=self.__chrome__).pack(side=LEFT, padx=self.PADX)
		self.tk_logins = dict()	# tkinter login credentials
		self.tk_login_entries = dict()
		for i in self.worker.MODULES:	# notebook tabs for the module configuration
			if i['login'] != None:
				frame_nb = ttk.Frame(nb_config)
				nb_config.add(frame_nb, text=i['name'])
				self.tk_logins[i['name']], self.tk_login_entries[i['name']] = self.__login_frame__(frame_nb, i['name'])
		frame_row = Frame(master)
		frame_row.pack(fill=X, expand=False)
		Button(frame_row, text="Save configuration", width=self.BUTTONWIDTH,
			command=self.__save_config__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		Button(frame_row, text="Load configuration", width=self.BUTTONWIDTH,
			command=self.__load_config__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		for i in ('README.md', 'README.txt', 'README.md.txt', 'README'):
			try:
				with open(self.storage.rootdir + self.storage.slash + i, 'r', encoding='utf-8') as f:
					self.about_help = f.read()
					Button(frame_row, text="About / Help", width=self.BUTTONWIDTH,
						command=self.__help__).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
					break
			except:
				continue
		Button(frame_row, text="Quit", width=self.BUTTONWIDTH,
			command=master.quit).pack(side=RIGHT, padx=self.PADX, pady=self.PADY)

	def __set_icon__(self, master):
		'Try to Somedo icon for the window'
		try:
			master.call('wm', 'iconphoto', master._w, PhotoImage(
				file='%s%ssomedo.png' % (self.storage.icondir, self.storage.slash)
			))
		except:
			pass

	def __login_frame__(self, frame, module, login=None):
		'Create Tk Frame for login credentials'
		tk_login = dict()
		tk_login_entry = dict()
		for i in self.worker.logins[module]:
			frame_row = Frame(frame)
			frame_row.pack(fill=BOTH, expand=True)
			Label(frame_row, text=i, anchor=E, padx=self.PADX, width=self.BUTTONWIDTH).pack(side=LEFT)
			tk_login[i] = StringVar(frame_row)
			if login != None:
				tk_login[i].set(login[i])
			tk_login_entry[i] = Entry(frame_row, textvariable=tk_login[i], show='*', width=self.BIGENTRY)
			tk_login_entry[i].pack(side=LEFT)
			tk_hide = BooleanVar(frame_row, True)
			Checkbutton(frame_row, text='hide', variable=tk_hide,
					command=partial(self.__hide_entry__, tk_login_entry[i], tk_hide)).pack(side=LEFT)
		return tk_login, tk_login_entry

	def __hide_entry__(self, entry, check):
		'Toggle hidden login credentials'
		if check.get():
			entry.config(show='*')
		else:
			entry.config(show='')

	def __job_dialog__(self, master, job, row):
		'Open window to edit a job'
		master.title(job['module'])
		frame_row = LabelFrame(master, text='Target(s)')
		frame_row.pack(fill=BOTH, expand=True)
		tk_job = {'module': job['module'], 'target': StringVar(frame_row, job['target'])}	# tk variables for the job configuration
		tk_target_entry = Entry(frame_row, textvariable=tk_job['target'], width=self.BIGENTRY)
		tk_target_entry.pack(side=LEFT)
		tk_job['options'] = dict()	# tk variables for the options
		if job['options'] != None:
			frame_grid = LabelFrame(master, text='Options')
			frame_grid.pack(fill=BOTH, expand=True)
			for i in self.worker.options[job['module']]:
				definition = self.worker.options[job['module']][i]
				value = job['options'][i]
				Label(frame_grid, text=definition['name']).grid(row=definition['row'], column=definition['column']*2, sticky=E)
				if isinstance(value, bool):	# checkbutton for boolean
					tk_job['options'][i] = BooleanVar(frame_grid, value)
					Checkbutton(frame_grid, variable=tk_job['options'][i]).grid(row=definition['row'], column=definition['column']*2+1, sticky=W)
					continue
				if isinstance(value, int):	# integer
					tk_job['options'][i] = IntVar(frame_grid, value)
				elif isinstance(value, str): # string
					tk_job['options'][i] = StringVar(frame_grid, value)
				Entry(frame_grid, textvariable=tk_job['options'][i]).grid(row=definition['row'], column=definition['column']*2+1, sticky=W)
		if job['login'] != None:
			frame_login = LabelFrame(master, text='Login')
			frame_login.pack(fill=BOTH, expand=True)
			tk_job['login'] = self.__login_frame__(frame_login, job['module'], login=job['login'])
		frame_row = Frame(master)
		frame_row.pack(fill=BOTH, expand=True)
		if row == len(self.jobs):
			Button(frame_row, text="Add job", width=self.BUTTONWIDTH,
				command=partial(self.__add_job__, master, tk_job, )).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		else:
			Button(frame_row, text="Remove job", width=self.BUTTONWIDTH,
			command=partial(self.__job_remove__, master, row)).pack(side=LEFT, padx=self.PADX, pady=self.PADY)
		Button(frame_row, text="Quit, do nothing", width=self.BUTTONWIDTH,
			command=master.destroy).pack(side=RIGHT, padx=self.PADX, pady=self.PADY)
		return tk_job

	def __get_login__(self, module):
		'Get login credentials for a module from root window'
		try:
			return { i: self.tk_logins[module][i].get() for i in self.worker.logins[module] }
		except TypeError:
			return None

	def __new_job__(self, module):
		'Create new job to add to job list'
		if len(self.jobs) == self.JOBLISTLENGTH - 1:	# check if free space in job list
			return
		job = self.worker.new_job(module)
		job['login'] = self.__get_login__(module)
		self.jobwindow = Tk()
		self.__job_dialog__(self.jobwindow, job, len(self.jobs))

	def __add_job__(self, master, tk_job):
		'Add job to list'
		master.destroy()
		job = {
			'module': tk_job['module'],
			'target': tk_job['target'].get(),
			'options': { i: tk_job['options'][i].get() for i in tk_job['options'] }
		}
		try:
			job['login'] = { i: tk_job['login'][i].get() for i in tk_job['login'] }
		except:
			job['login'] = None
		self.jobs.append(job)	# append new job to the job list
		self.__update_joblist__()

	def __job_edit__(self, row):
		'Edit or remove jobin job list'
		self.jobwindow = Tk()
		self.__job_dialog__(self.jobwindow, self.jobs[row], row)

	def __purge_jobs__(self):
		'Purge job list'
		if messagebox.askyesno('Purge job list', 'Are you sure?'):
			self.jobs = []
			self.__update_joblist__()

	def __job_text__(self, row):
		'Generate string for one job button'
		if row >= len(self.jobs):
			return ''
		return '%02d: %s - %s' % (row+1, self.jobs[row]['module'], self.jobs[row]['target'])

	def __update_joblist__(self):
		'Update the list of jobs'
		for i in range(self.JOBLISTLENGTH):
			self.tk_jobbuttons[i].set(self.__job_text__(i))

	def __job_up__(self, row):
		'Move job up in list'
		if row > 0:
			self.jobs[row], self.jobs[row-1] = self.jobs[row-1], self.jobs[row]
			self.__update_joblist__()

	def __job_down__(self, row):
		'Move job down in list'
		if row < ( len(self.jobs) - 1 ) :
			self.jobs[row], self.jobs[row+1] = self.jobs[row+1], self.jobs[row]
			self.__update_joblist__()

	def __job_remove__(self, master, row):
		'Remove job from list'
		if messagebox.askyesno('Job %02d' % (row+1), 'Remove job from list?'):
			master.destroy()
			self.jobs.pop(row)
			self.__update_joblist__()

	def __output_dir__(self):
		'Set path to output directory.'
		path = filedialog.askdirectory(initialdir="~/",title='Destination directory')
		if path != ():
			self.tk_outdir_entry.delete(0, END)
			self.tk_outdir_entry.insert(0, path)
			self.storage.outdir = path

	def __chrome__(self):
		'Set path to chrome.'
		path = filedialog.askopenfilename(title = 'chrome', filetypes = [('All files', '*.*')])
		if path != () and path !=  '':
			self.tk_chrome_entry.delete(0, END)
			self.tk_chrome_entry.insert(0, path)
			self.chrome.path = path

	def __save_config__(self):
		'Save configuration to file.'
		path = filedialog.asksaveasfilename(title = 'Configuration file', filetypes = [('Somedo configuration files', '*.smdc')])
		if path[-5:] != '.smdc':
			path += '.smdc'
		try:
			self.storage.json_dump({
				'Output': self.tk_outdir.get(),
				'Chrome': self.tk_chrome.get(),
				'Modules': { i['name']: self.__get_login__(i['name']) for i in self.worker.MODULES if i['login'] != None }
			}, path)
		except:
			messagebox.showerror('Error', 'Could not save configuration file')

	def __load_config__(self):
		'Load configuration from file.'
		path = filedialog.askopenfilename(title = 'Configuration file', filetypes = [('Somedo configuration files', '*.smdc'), ('All files', '*.*')])
		if path != () and path !=  '':
			try:
				config = self.storage.json_load(path)
			except:
				messagebox.showerror('Error', 'Could not load configuration file')
				return
			try:
				self.tk_outdir_entry.delete(0, END)
				self.tk_outdir_entry.insert(0, config['Output'])
				self.storage.outdir = config['Output']
				self.tk_chrome_entry.delete(0, END)
				self.tk_chrome_entry.insert(0, config['Chrome'])
				self.chrome.path = config['Chrome']
				for i in config['Modules']:
					for j in config['Modules'][i]:
						self.tk_login_entries[i][j].delete(0, END)
						self.tk_login_entries[i][j].insert(0, config['Modules'][i][j])
			except:
				messagebox.showerror('Error', 'Could not decode configuration file')

	def __help__(self):
		'Open window to show About / Help'
		help_win = Tk()
		help_win.wm_title('About / Help')
		text = Text(help_win, padx=2, pady=2, height=35, width=160)
		text.bind("<Key>", lambda e: "break")
		text.insert(END, self.about_help)
		text.pack(padx=2, pady=2)
		Button(help_win, text="Close", width=6, command=help_win.destroy).pack(padx=2, pady=2, side=RIGHT)

	def __start__(self, headless=True):
		'Start the jobs'
		self.headless = headless
		if len(self.jobs) < 1:
			return
		try:	# check if task is running
			if self.thread.isAlive():
				return
		except:
			self.stop = Event()	# to stop main thread
			self.thread = Thread(target=self.__thread__)	# define main thread
			self.thread.start()	# start thread
		else:
			messagebox.showerror('Error', 'Nothing to do. Add jobs.')

	def __start_hidden__(self):
		'Start working with Chrome in headless mode'
		if len(self.jobs) > 0:
			try:	# check if task is running
				if self.thread.isAlive():
					return
			except:
				pass
			self.__running_label__.config(background='red')
			self.__tk_running__.set("Running...")
			self.headless = True	# chrome will be started with option --headless
			self.stop = Event()	# to stop main thread
			self.thread = Thread(target=self.__thread__)	# define main thread
			self.thread.start()	# start thread
		else:
			messagebox.showerror('Error', 'Nothing to do')

	def __stop__(self):
		'Stop running job but give results based on so far sucked data'
		try:	# check if task is running
			if self.thread.isAlive() and messagebox.askyesno('Somedo', 'Stop running task?'):
				self.stop.set()
		except:
			pass

	def __thread__(self):
		'Execute jobs'
		msg = self.worker.execute(self.jobs, self.__get_config__(), headless=self.headless, stop=self.stop)
		self.__tk_running__.set("")
		self.__running_label__.config(background='white')
		messagebox.showinfo('Done', msg)

if __name__ == '__main__':	# start here if called as program / app
	rootwindow = Tk()
	GuiRoot(rootwindow)
	rootwindow.mainloop()