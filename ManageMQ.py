import stomp
import urllib3
import urllib3.util
import json
import tkinter as tk
from time import sleep

http = urllib3.PoolManager()
headers = urllib3.util.make_headers(basic_auth='admin:admin')

class Listener(stomp.ConnectionListener):
    def on_error(self, frame):
        return super().on_error(frame)

    def on_message(self, frame):
        return super().on_message(frame)

conn = stomp.Connection([('localhost', 61613)], auto_content_length=False, heartbeats=(4000, 4000))
conn.set_listener('', Listener())
conn.connect('admin', 'admin', wait=True, headers={'client-id': 'admin'})
    
class Queue:
    def __init__(self, name, type, pos, master):
        self.name = name
        self.type = type
        self.master = master
        if type == 'topic':
            self.subs = []
            topics = self.master.getQueuesAndTopics()
            for topic in topics[1]:
                topic = topic.split()
                if topic[0] == self.name:
                    try:
                        self.subs.append(topic[1])
                    except:
                        pass
        tk.Label(master.scrollFrame, text=f'{name}').grid(row=pos, column=0, pady=20)
        tk.Label(master.scrollFrame, text=f'{self.type}').grid(row=pos, column=1, padx=20, pady=20)
        if type == 'queue':
            mens_p = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{name}",subcomponent=queues,routing-type="anycast",queue="{name}"/countMessages()', headers=headers).json()
            mens_p = mens_p['value']
            tk.Label(master.scrollFrame, text=f"{mens_p}").grid(row=pos, column=2, padx=20, pady=20)
            tk.Button(master.scrollFrame, text='BrowseMessages', command=self.browseMessages).grid(row=pos, column=3, pady=20)
        elif type == 'topic':
            total_mens_p = 0
            for subscriber in self.subs:
                mens_p = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{name}",subcomponent=queues,routing-type="multicast",queue="{name} {subscriber}"/countMessages()', headers=headers).json()
                mens_p = mens_p['value']
                total_mens_p += mens_p
            tk.Label(master.scrollFrame, text=f"{total_mens_p}").grid(row=pos, column=2, padx=20, pady=20)
            tk.Button(master.scrollFrame, text='ListSubscribers', command=self.printSubscribers).grid(row=pos, column=3)
        tk.Button(master.scrollFrame, text='SendMessage', command=self.sendMessage).grid(row=pos, column=4, padx=20, pady=20)
        tk.Button(master.scrollFrame, text='Delete', command=self.deleteQueueWindow).grid(row=pos, column=5, pady=20)

    def browseMessages(self, topic_name = None):
        window = tk.Toplevel(self.master.master, width=300, height=200)
        if topic_name:
            messages = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{topic_name}",subcomponent=queues,routing-type="multicast",queue="{topic_name} {self.name}"/browse()', headers=headers).json()
        else:
            messages = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{self.name}",subcomponent=queues,routing-type="anycast",queue="{self.name}"/browse()', headers=headers).json()
        if messages['status'] == 200:
            counter = 0
            if messages['value'] == []:
                tk.Label(window, text='Não há menssagems!').pack(padx=10, pady=10)
            for message in messages['value']:
                try:
                    origin = message['StringProperties']['name']
                except:
                    origin = 'Unknown'
                tk.Label(window, text=f'From {origin}: {message["text"]}').grid(row=counter, column=0, padx=20, pady=20)
                tk.Button(window, text='Delete', command=lambda msg = message: self.deleteMessage(window, self.name, msg['messageID'], topic_name=topic_name)).grid(row=counter, column=1, padx= 10, pady=20)
                counter += 1
        else:
            tk.Label(window, text=f'{messages["error"]}').pack()
            tk.Button(window, text='Ok', command=window.destroy).pack(side='bottom')

    def deleteMessage(self, window, queue, id, topic_name = None):
        if topic_name:
            response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{topic_name}",subcomponent=queues,routing-type="multicast",queue="{topic_name} {queue}"/removeMessage/{id}', headers=headers).json()
        else:
            response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{queue}",subcomponent=queues,routing-type="anycast",queue="{queue}"/removeMessage/{id}', headers=headers).json()
        if response['status'] == 200:
            window.destroy()
            self.browseMessages()
            sleep(0.01)
            self.master.update()
        else:
            self.master.popupWindow(f'{response["error"]}')

    def printSubscribers(self):
        window = tk.Toplevel(self.master.master)
        if self.subs == []:
            tk.Label(window, text='Não há subscritos!').pack(padx=10, pady=10)
            return
        tk.Label(window, text='Nome').grid(row=0, column=0)
        tk.Label(window, text='Mens. Pendentes').grid(row=0, column=1)
        counter = 0
        for subscriber in self.subs:
            counter += 1
            tk.Label(window, text=f'{subscriber}').grid(row=counter, column=0)
            mens_p = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0",component=addresses,address="{self.name}",subcomponent=queues,routing-type="multicast",queue="{self.name} {subscriber}"/countMessages()', headers=headers).json()
            mens_p = mens_p['value']
            tk.Label(window, text=f'{mens_p}').grid(row=counter, column=1)
            tk.Button(window, text='BrowseMessages', command=lambda sub = subscriber: self.master.queues[f'{sub}'].browseMessages(topic_name = self.name)).grid(row=counter, column=2)

    def sendMessage(self):
        window = tk.Toplevel(self.master.master, height=200, width=300)
        tk.Label(window, text='Digite a messagem a ser enviada:').pack()
        entry = tk.Entry(window, width=50)
        entry.pack()
        tk.Button(window, text='Enviar', command=lambda: [conn.send(self.name, entry.get(), headers={'persistent': True, 'name': 'admin'}), window.destroy(), sleep(0.1), self.master.update()]).pack(side='bottom')
        entry.bind('<Return>', lambda e: [conn.send(self.name, entry.get(), headers={'persistent': True, 'name': 'admin'}), window.destroy(), self.master.update()])
        window.focus_force()
        entry.focus()

    def deleteQueueWindow(self):
        window = tk.Toplevel(self.master, height=200, width=300)
        if self.type == 'queue':
            tk.Label(window, text=f'Você tem certeza que quer deletar a queue {self.name}?').pack(padx=20, pady=5)
        elif self.type == 'topic':
            tk.Label(window, text=f'Você tem certeza que quer deletar o tópico {self.name}?').pack(padx=20, pady=5)
        tk.Button(window, text='Sim', command=lambda: [self.deleteQueue(), window.destroy()]).pack(side='left', padx=50, pady=5)
        tk.Button(window, text='Não', command=window.destroy).pack(side='right', padx=50, pady=5)
        window.focus_force()

    def deleteQueue(self):
        if self.type == 'queue':
            response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/destroyQueue(java.lang.String)/{self.name}', headers=headers).json()
        elif self.type == 'topic':
            response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/deleteAddress(java.lang.String,boolean)/{self.name}/true', headers=headers).json()
        if response['status'] == 200:
            sleep(0.01)
            self.master.update()
            self.master.popupWindow('Queue deletada com sucesso!')
        else:
            self.master.popupWindow(response['Error'])

class Main_menu(tk.Frame):

    q_counter = 0
    queues = {}
    topics = {}

    def __init__(self, master):
        super().__init__(master, height=500, width=600)
        self.pack(fill='x', expand=True)
        self.master = master

        tk.Label(self, text='Gerenciador do broker').pack(side='top', padx=10, pady=10)

        self.scrollBar = tk.Scrollbar(self, orient='vertical')
        self.scrollBar.pack(side='right', fill='y')

        self.canvas = tk.Canvas(self, width=550, height=400)
        self.canvas.pack(fill='x')

        self.scrollBar.configure(command=self.canvas.yview)
        self.drawFrame()

        self.frame = self.canvas.create_window((0, 0), window=self.scrollFrame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollBar.set)

        tk.Button(self, text='Create Queue', command=self.createQueueWindow).pack(side='left', padx=50, pady=10)
        tk.Button(self, text='Create Topic', command=self.createTopicWindow).pack(side='left', padx=50, pady=10)
        tk.Button(self, text='Update', command=self.update).pack(side='left', padx=50, pady=10)

        self.update()

    def drawFrame(self):
        self.scrollFrame = tk.Frame(self.canvas, width=550, height=400, bg='white')
        self.scrollFrame.pack(fill='both', expand=True)

        tk.Label(self.scrollFrame, text='Nome').grid(row=0, column=0)
        tk.Label(self.scrollFrame, text='Tipo').grid(row=0, column=1, padx=20)
        tk.Label(self.scrollFrame, text='Mens. Pendentes').grid(row=0, column=2)

        self.scrollFrame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

    def update(self):
        self.canvas.delete(self.frame)
        self.scrollFrame.destroy()
        self.queues = {}
        self.topics = {}
        self.drawFrame()
        self.frame = self.canvas.create_window((0, 0), window=self.scrollFrame, anchor='nw')
        queueNames = self.getQueuesAndTopics()
        self.printQueuesAndTopics(queueNames)

    def getQueuesAndTopics(self):
        response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/getQueueNames/ANYCAST', headers=headers).json()
        queues = response['value']
        response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/getQueueNames/MULTICAST', headers=headers).json()
        topics = response['value']
        return [queues, topics]

    def printQueuesAndTopics(self, queueNames):
        self.q_counter = 0
        for q_name in queueNames[0]:
            self.q_counter += 1
            self.queues[f'{q_name}'] = Queue(q_name, 'queue', self.q_counter, self)
        topic_names = []
        for t_name in queueNames[1]:
            t_name = t_name.split()[0]
            if t_name not in topic_names:
                topic_names.append(t_name)
                self.q_counter += 1
                self.topics[f'{t_name}'] = Queue(t_name, 'topic', self.q_counter, self)
        if self.q_counter > 8:
            self.scrollFrame.configure(height=self.q_counter * 50)

    def createQueueWindow(self):
        window = tk.Toplevel(self.master, height=200, width=300)
        tk.Label(window, text='Digite o nome da Queue:').pack()
        entry = tk.Entry(window, width=50)
        entry.pack(padx=10)
        tk.Button(window, text='Criar', command=lambda: [self.createQueue(entry.get(), 'queue'), window.destroy()]).pack(side='bottom', pady=5)
        window.focus_force()
        entry.focus()

    def createTopicWindow(self):
        window = tk.Toplevel(self.master, height=200, width=300)
        tk.Label(window, text='Digite o nome do Tópico:').pack()
        entry = tk.Entry(window, width=50)
        entry.pack(padx=10)
        tk.Button(window, text='Criar', command=lambda: [self.createQueue(entry.get(), 'topic'), window.destroy()]).pack(side='bottom', pady=5)
        window.focus_force()
        entry.focus()

    def createQueue(self, name, type):
        if name:
            if type == 'queue':
                q_json = json.dumps({"name": name, "address": name, "routing-type": "ANYCAST", "durable": True})
            elif type == 'topic':
                if ' ' in name:
                    self.popupWindow('Favor não utilizar espaços no nome!')
                    return
                q_json = json.dumps({"name": name, "address": name, "routing-type": "MULTICAST", "durable": True})
            response = http.request('GET', f'http://localhost:8161/console/jolokia/exec/org.apache.activemq.artemis:broker="0.0.0.0"/createQueue(java.lang.String)/{q_json}', headers=headers).json()
            if response['status'] == 200:
                self.popupWindow('Queue criada com êxito!')
                sleep(0.01)
                self.update()
            else:
                self.popupWindow(f'{response["error"]}')

    def popupWindow(self, msg):
        popup = tk.Toplevel(self.master, width=300, height=200)
        tk.Label(popup, text=f'{msg}').pack()
        tk.Button(popup, text='Ok', command=popup.destroy).pack(side='bottom')
        popup.focus_force()
    

root = tk.Tk()
root.title('Broker Manager')
root.geometry('600x500')
menu = Main_menu(root)
root.mainloop()
