from utils import LinkedList
from typing import * 
from threading import * 


class Node:
    __ID: ClassVar[int] = 0
    __ID_LOCK: ClassVar[Lock] = Lock()

    def __init__(self):
        self._id: int = Node.__get_id__()
        self._next: Node = None

    def __str__(self) -> str:
        return f"N{self._id}"

    @classmethod
    def __get_id__(cls) -> int:
        Node.__ID_LOCK.acquire(blocking=True)
        id = Node.__ID
        Node.__ID += 1
        Node.__ID_LOCK.release()
        return id

nodes = []
for i in range(10):
    nodes.append(Node())
ll = LinkedList(nodes)
print(ll)
# print(nodes[4])
for i in range(len(nodes)):
    print(nodes[i])
    ll.move_down(nodes[i])
    print(ll)
    # ll.move_up(nodes[i])
    # print(ll)