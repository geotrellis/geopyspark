class SingletonBase(type):
    _cls_instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._cls_instances:
            cls._cls_instances[cls] = super(SingletonBase, cls).__call__(*args, **kwargs)
        return cls._cls_instances[cls]
