# Master Prompt Template — Initial Generation (Shot 0)

This is the only template used for prompts. Iterative resolution (shots 1-10)
is handled during evaluation with real error output — see todo_notes.md.

```
TASK: {task_title}

{task_description}

FUNCTIONAL REQUIREMENTS:
{functional_requirements}

Create a complete {language} project for a clean Ubuntu 22.04 machine
with only {language_runtime} installed. Include:
- Source code
- {dependency_file} with all dependencies (direct and transitive)
  pinned to exact versions
- README.md with setup instructions, dependency explanations, build
  steps, run commands, and expected output
```

## Language Parameters

| Placeholder          | Python           | Java             | JavaScript        | C++                     |
|----------------------|------------------|------------------|-------------------|-------------------------|
| `{language}`         | Python           | Java             | JavaScript        | C++                     |
| `{dependency_file}`  | requirements.txt | pom.xml          | package.json      | CMakeLists.txt          |
| `{language_runtime}` | Python 3.10+     | JDK 17+          | Node.js 20+ (LTS) | G++ 12+ and CMake 3.22+ |

## How to use

1. Pick a task (p_01 through p_50) — the task_title, task_description, and
   functional_requirements are identical across all languages
2. The pre-filled prompts in each language subfolder are ready to copy-paste
3. Send the complete prompt to the LLM agent as a fresh conversation
4. For stochastic trials, send the exact same prompt again in a new conversation
