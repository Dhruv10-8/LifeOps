import { useEffect, useState } from "react";

type Task = {
  id: number;
  title: string;
  completed: boolean;
};

// REMOVED: No more hardcoded GitHub Codespaces URLs!
const API_BASE = "/api"; 

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState("");

  const loadTasks = async () => {
    const res = await fetch(`${API_BASE}/tasks/`); // Hits /api/tasks/
    const data = await res.json();
    setTasks(data);
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const addTask = async () => {
    if (!newTask.trim()) return;

    await fetch(`${API_BASE}/tasks/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: newTask,
      }),
    });

    setNewTask("");
    loadTasks();
  };

  const toggleTask = async (id: number) => {
    await fetch(`${API_BASE}/tasks/${id}/`, {
      method: "PUT",
    });

    loadTasks();
  };

  const deleteTask = async (id: number) => {
    await fetch(`${API_BASE}/tasks/${id}/`, {
      method: "DELETE",
    });

    loadTasks();
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>LifeOps</h1>

      <div>
        <input
          value={newTask}
          placeholder="Enter task"
          onChange={(e) => setNewTask(e.target.value)}
        />

        <button onClick={addTask}>
          Add Task
        </button>
      </div>

      <hr />

      <h2>Tasks</h2>

      {tasks.length === 0 ? (
        <p>No tasks yet</p>
      ) : (
        <ul>
          {tasks.map((task) => (
            <li key={task.id}>
              {task.completed ? "✅" : "⬜"} {task.title}

              <button onClick={() => toggleTask(task.id)}>
                Toggle
              </button>

              <button onClick={() => deleteTask(task.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;