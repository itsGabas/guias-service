from typing import Dict, List, Optional
from app.models.client import Client
from app.models.task import Task
from app.models.email_log import EmailLog
from app.models.task_template import TaskTemplate
import re


class MockRepository:
    def __init__(self):
        self._clients: Dict[str, Client] = {}
        self._tasks: Dict[str, Task] = {}
        self._email_logs: Dict[str, EmailLog] = {}
        self._templates: Dict[str, TaskTemplate] = {}

    # ── CLIENTS ───────────────────────────────────────────────────────

    def save_client(self, client: Client) -> Client:
        self._clients[client.id] = client
        return client

    def get_client(self, client_id: str) -> Optional[Client]:
        return self._clients.get(client_id)

    def delete_client(self, client_id: str) -> bool:
        if client_id in self._clients:
            del self._clients[client_id]; return True
        return False

    def get_client_by_cnpj(self, cnpj: str) -> Optional[Client]:
        digits = re.sub(r'\D', '', cnpj)
        for c in self._clients.values():
            if c.cnpj_digits() == digits:
                return c
        return None

    def get_client_by_ie(self, ie: str) -> Optional[Client]:
        ie_digits = re.sub(r'\D', '', ie)
        if len(ie_digits) < 5: return None
        for c in self._clients.values():
            if c.ie_digits() and c.ie_digits() == ie_digits:
                return c
        return None

    def list_clients(self, active_only: bool = True) -> List[Client]:
        clients = list(self._clients.values())
        if active_only:
            clients = [c for c in clients if c.active]
        return sorted(clients, key=lambda c: c.company_name)

    # ── TASKS ─────────────────────────────────────────────────────────

    def save_task(self, task: Task) -> Task:
        self._tasks[task.id] = task; return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, client_id=None, status=None, department=None) -> List[Task]:
        tasks = list(self._tasks.values())
        if client_id:  tasks = [t for t in tasks if t.client_id == client_id]
        if status:     tasks = [t for t in tasks if t.status.value == status]
        if department: tasks = [t for t in tasks if t.department.value == department]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]; return True
        return False

    # ── EMAIL LOGS ────────────────────────────────────────────────────

    def save_email_log(self, log: EmailLog) -> EmailLog:
        self._email_logs[log.id] = log; return log

    def get_logs_by_task(self, task_id: str) -> List[EmailLog]:
        return [l for l in self._email_logs.values() if l.task_id == task_id]

    def get_logs_by_client(self, client_id: str) -> List[EmailLog]:
        return sorted([l for l in self._email_logs.values() if l.client_id == client_id],
                      key=lambda l: l.sent_at, reverse=True)

    def list_all_logs(self) -> List[EmailLog]:
        return sorted(self._email_logs.values(), key=lambda l: l.sent_at, reverse=True)

    # ── TASK TEMPLATES ────────────────────────────────────────────────

    def save_template(self, template: TaskTemplate) -> TaskTemplate:
        self._templates[template.id] = template; return template

    def get_template(self, template_id: str) -> Optional[TaskTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[TaskTemplate]:
        return sorted(self._templates.values(), key=lambda t: t.created_at, reverse=True)

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]; return True
        return False

    def match_template(self, text: str) -> Optional[TaskTemplate]:
        for t in self._templates.values():
            matched, _, _ = t.matches(text)
            if matched: return t
        return None

    # ── STATS ─────────────────────────────────────────────────────────

    def stats(self) -> dict:
        from app.models.enums import TaskStatus
        return {
            "total_clients":         len(self._clients),
            "total_tasks":           len(self._tasks),
            "tasks_pendentes":       sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDENTE),
            "tasks_enviadas":        sum(1 for t in self._tasks.values() if t.status == TaskStatus.ENVIADA),
            "tasks_concluidas":      sum(1 for t in self._tasks.values() if t.status == TaskStatus.CONCLUIDA),
            "total_emails_enviados": sum(1 for l in self._email_logs.values() if l.status.value == "ENVIADO"),
            "total_emails_falhos":   sum(1 for l in self._email_logs.values() if l.status.value == "FALHOU"),
        }
