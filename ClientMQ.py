import stomp
import urllib3
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

http = urllib3.PoolManager()
headers = urllib3.util.make_headers(basic_auth='admin:admin')

class Listener(stomp.ConnectionListener):
    def on_error(self, frame):
        client.message(f'Error: {frame.body}')
    
    def on_message(self, frame):
        try:
            origin = frame.headers['name']
        except:
            origin = 'Unknown'
        if frame.headers['destination'] == client.name:
            client.message(f'{origin}: {frame.body}')
        else:
            try:
                client.topics[f'{frame.headers["destination"]}'].message(f'{origin}: {frame.body}')
            except:
                pass

class Topic(tk.Toplevel):
    def __init__(self, master, t_name):
        self.master = master
        self.t_name = t_name
        self.open = False

    def start(self):
        if self.open:
            return
        
        super().__init__(self.master, height=400, width=400)
        tk.Label(self, text=f'Tópico {self.t_name}').pack(padx=20, pady=10)

        self.textBox = ScrolledText(self, wrap=tk.WORD, state='disabled')
        self.textBox.config(height=20, width=50)
        self.textBox.pack(side='top', padx=5, pady=5)

        tk.Label(self, text='Send a message:').pack(side='left', padx=5)
        self.entry = tk.Entry(self, width=50)
        self.entry.pack(side='left', padx=5)
        self.entry.bind('<Return>', self.send_message)
        self.entry.focus()

        self.open = True
        client.conn.subscribe(f'{self.t_name}::{self.t_name} {client.name}', id=f'{client.name}/{self.t_name}', headers={'subscription-type': 'MULTICAST', 'durable-subscription-name': f'{client.name}'})
        self.protocol('WM_DELETE_WINDOW', self.close_window)

    def send_message(self, event = None):
        msg = self.entry.get()
        if msg:
            self.entry.delete(0, tk.END)
            client.conn.send(self.t_name, msg, headers={'persistent': True, 'name': client.name})

    def message(self, msg):
        self.textBox.config(state='normal')
        self.textBox.insert(tk.END, msg + '\n')
        self.textBox.see('end')
        self.textBox.config(state='disabled')

    def close_window(self):
        client.conn.unsubscribe(f'{client.name}/{self.t_name}')
        self.open = False
        self.destroy()

class Client:
    def __init__(self, master):
        self.master = master
        self.master.geometry('200x200')
        self.frame = tk.Frame(master)
        self.frame.pack(fill='both')

        tk.Label(self.frame, text='Digite o seu nome: ').pack(padx=10, pady=10)
        entry = tk.Entry(self.frame, width=30)
        entry.pack(pady=10)
        tk.Button(self.frame, text='Entrar', command=lambda: self.login(entry.get())).pack(side='bottom', pady=10)
        entry.bind('<Return>', lambda event: self.login(entry.get()))
        entry.focus()

    def login(self, name, event = None):
        if name:
            self.name = name        
        else:
            return
        
        self.frame.destroy()
        self.master.geometry('400x400')
        self.master.title(self.name)
        self.frame = tk.Frame(self.master)
        self.frame.pack(fill='both')

        tk.Label(self.frame, text='Main feed').pack(padx=10)
        self.textBox = ScrolledText(self.frame, wrap = tk.WORD, state='disabled')
        self.textBox.config(height=20, width=300)
        self.textBox.pack(side='top', padx=5, pady=5)

        tk.Button(self.frame, text='Enviar Menssagem', command=self.send_message_window).pack(side='left', padx=10, pady=10)
        tk.Button(self.frame, text='Subscrever', command=self.subscription_window).pack(side='left', padx=10, pady=10)
        tk.Button(self.frame, text='Listar Tópicos', command=self.listTopics).pack(side='left', padx=10, pady=10)

        self.get_topics()

        self.conn = stomp.Connection([('localhost', 61613)], auto_content_length=False, heartbeats=(4000, 4000))
        self.conn.set_listener('', Listener())
        self.conn.connect('admin', 'admin', wait=True, headers={'client-id': name})
        self.conn.subscribe(name, id=name, headers={'subscription-type': 'ANYCAST', 'durable-subscription-name': name})
        
    def get_topics(self):
        self.topics = {}
        response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/getQueueNames/MULTICAST', headers=headers).json()
        for topic in response['value']:
            topic = topic.split()
            if topic[0] not in self.topics.keys():
                try:
                    if topic[1] == self.name:
                        self.topics[topic[0]] = Topic(self.master, topic[0])
                except:
                    pass

    def subscription_window(self):
        window = tk.Toplevel(self.master, height=200, width=300)
        tk.Label(window, text='Digite o nome do tópico para se subscrever').pack()
        tk.Label(window, text='(Caso o tópico não exista, ele será criado!)').pack()
        entry = tk.Entry(window, width=50)
        entry.pack(side='bottom', padx=10, pady=10)
        entry.bind('<Return>', lambda e: self.subscribe2topic(entry.get(), window))
        entry.focus()

    def subscribe2topic(self, t_name, window, event = None):
        if t_name:
            window.destroy()
            if t_name in self.topics.keys():
                self.message('[SYSTEM] Você já está subscrito neste tópico!')
                return
            self.topics[f'{t_name}'] = Topic(self.master, t_name)

    def listTopics(self):
        window = tk.Toplevel(self.master, width=300, height=300)
        if self.topics == {}:
            tk.Label(window, text='Você não está subscrito em nenhum tópico!').grid(row=0, column=0, padx=10, pady=10)
        else:
            tk.Label(window, text='Tópicos subscritos:').grid(row=0, column=0, padx=10, pady=10)
        counter = 0
        for topic in list(self.topics.keys()):
            counter += 1
            tk.Label(window, text=f'{topic}').grid(row=counter, column=0)
            tk.Button(window, text='Abrir', command=lambda topic=topic: [self.topics[topic].start(), window.destroy()]).grid(row=counter, column=1, padx=5, pady=5)
            tk.Button(window, text='Desinscrever', command=lambda topic=topic: self.unsub(topic, window)).grid(row=counter, column=2, padx=5, pady=5)

    def unsub(self, topic, window):
        response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/destroyQueue(java.lang.String)/{topic} {self.name}', headers=headers).json()
        if response['status'] == 200:
            del self.topics[topic]
            window.destroy()
            self.listTopics()
        else:
            self.message(response['Error'])

    def send_message_window(self):
        window = tk.Toplevel(self.master, height=200, width=300)
        tk.Label(window, text='Nome do destinatário:').pack()
        self.target_entry = tk.Entry(window, width=50)
        self.target_entry.pack()
        tk.Label(window, text='Mensagem:').pack()
        self.msg_entry = tk.Entry(window, width=50)
        self.msg_entry.pack()
        tk.Button(window, text='Enviar', command=lambda: self.send_message(window)).pack(side='bottom', pady=5)

    def send_message(self, window):
        target = self.target_entry.get()
        msg = self.msg_entry.get()
        if target and msg:
            window.destroy()
            request = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{target}",subcomponent=queues,routing-type="anycast",queue="{target}"/browse()', headers=headers).json()
            if request['status'] != 200:
                self.message(f'cliente {target} não existe!')
                return
            self.conn.send(target, msg, headers={'persistent': True, 'name': self.name})

    def message(self, msg):
        self.textBox.config(state='normal')
        self.textBox.insert(tk.END, msg + '\n')
        self.textBox.see('end')
        self.textBox.config(state='disabled')

root = tk.Tk()
client = Client(root)
root.mainloop()
