from .storage import Storage

class Config:
    def __init__(self, db_file=None):
        self.storage = Storage(db_file=db_file)
        self._defaults = {
            'max_retries': 3,
            'backoff_base': 2,
        }

    def get(self, key):
        return self.storage.get_config(key, self._defaults.get(key))

    def set(self, key, value):
        if key not in self._defaults:
            raise KeyError(f"Invalid config key: {key}")
        
        # Ensure value is of the correct type
        if isinstance(self._defaults[key], int):
            value = int(value)
        
        self.storage.set_config(key, value)
        return {key: value}

    def get_all(self):
        config = {}
        for key in self._defaults:
            config[key] = self.get(key)
        return config
