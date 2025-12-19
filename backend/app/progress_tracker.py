import asyncio

class ProgressTracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgressTracker, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        self.status = "Idle"
        self.percent = 0
        self.logs = []
        self.is_running = False

    def start(self, task_name="Processing"):
        self.reset()
        self.status = task_name
        self.is_running = True
        
    def update(self, status=None, percent=None, log=None):
        if status:
            self.status = status
        if percent is not None:
            self.percent = percent
        if log:
            # Keep only last 50 logs to avoid memory bloat
            self.logs.append(log)
            if len(self.logs) > 50:
                self.logs.pop(0)
    
    def complete(self):
        self.percent = 100
        self.status = "Completed"
        self.is_running = False
        
    def get_status(self):
        return {
            "status": self.status,
            "percent": self.percent,
            "logs": self.logs,
            "is_running": self.is_running
        }

# Global instance
tracker = ProgressTracker()
