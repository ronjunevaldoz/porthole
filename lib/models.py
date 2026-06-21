from dataclasses import dataclass


@dataclass
class Service:
    name:        str
    local_port:  int
    remote_port: int
    local_host:  str = ""
