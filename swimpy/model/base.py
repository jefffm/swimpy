import msgpack
from booby.models import Model


class BaseModel(Model):
    @classmethod
    def from_msgpack(cls, msgpack_str):
        data = msgpack.unpackb(msgpack_str.strip(), use_list=False, encoding='utf-8')
        data.pop('type')  # remove the type header from the data dict before instantiating the model
        return cls(**data)

    @property
    def to_msgpack(self):
        return msgpack.packb(dict(self), use_bin_type=True)
