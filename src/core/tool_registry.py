"""
Register Commands as LLM-callable tools.
"""
from typing import Any, Dict, Optional

from src.core.tools import get_registry, register_tool


def register_command_tools(commands):
    """
    Register Commands methods as LLM-callable tools.

    Args:
        commands: Commands instance
    """
    registry = get_registry()

    # Git command tool
    def git_handler(command: str) -> Dict[str, Any]:
        """Execute git command and return output."""
        import shlex
        import subprocess

        try:
            git_args = ["git"] + shlex.split(command) if command.strip() else ["git"]
            env = dict(subprocess.os.environ)
            env["GIT_EDITOR"] = "true"
            result = subprocess.run(
                git_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                shell=False,
                encoding=commands.io.encoding,
                errors="replace",
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "return_code": result.returncode,
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error: {str(e)}",
                "return_code": -1,
            }

    register_tool(
        name="git",
        description="Execute a git command. Returns the output of the command.",
        parameters={
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The git command to execute (e.g., 'status', 'log --oneline -5', 'diff')",
                }
            },
        },
        handler=git_handler,
    )

    # Web scraping tool
    def web_handler(url: str) -> Dict[str, Any]:
        """Scrape a webpage and return content."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if not commands.scraper:
            from src.web.scrape import Scraper, install_playwright

            disable_playwright = getattr(commands.args, "disable_playwright", False)
            playwright_available = False
            if not disable_playwright:
                playwright_available = install_playwright(commands.io)

            commands.scraper = Scraper(
                print_error=commands.io.tool_error,
                playwright_available=playwright_available,
                verify_ssl=commands.verify_ssl,
            )

        content = commands.scraper.scrape(url)
        if content:
            return {
                "success": True,
                "url": url,
                "content": f"Here is the content of {url}:\n\n" + content,
            }
        else:
            return {
                "success": False,
                "url": url,
                "content": "Failed to scrape the webpage.",
            }

    register_tool(
        name="web_scrape",
        description="Scrape a webpage and convert it to markdown. Use this to get information from websites.",
        parameters={
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape (protocol optional, https:// will be added if missing)",
                }
            },
        },
        handler=web_handler,
    )

    # Run shell command tool
    def run_handler(command: str) -> Dict[str, Any]:
        """Run a shell command and return output."""
        from src.utils.run_cmd import run_cmd

        exit_status, combined_output = run_cmd(
            command,
            verbose=commands.verbose,
            error_print=commands.io.tool_error,
            cwd=commands.coder.root,
        )

        return {
            "success": exit_status == 0,
            "output": combined_output or "",
            "exit_status": exit_status,
        }

    register_tool(
        name="run_command",
        description="Run a shell command and get its output. Use this to execute terminal commands, run scripts, check file contents, etc.",
        parameters={
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                }
            },
        },
        handler=run_handler,
    )

    # List files tool
    def list_files_handler() -> Dict[str, Any]:
        """List files in the repository and chat."""
        files = commands.coder.get_all_relative_files()
        chat_files = []
        other_files = []

        for file in files:
            abs_file_path = commands.coder.abs_root_path(file)
            if abs_file_path in commands.coder.abs_fnames:
                chat_files.append(file)
            else:
                other_files.append(file)

        read_only_files = [
            commands.coder.get_rel_fname(f) for f in commands.coder.abs_read_only_fnames
        ]

        return {
            "chat_files": sorted(chat_files),
            "other_files": sorted(other_files),
            "read_only_files": sorted(read_only_files),
        }

    register_tool(
        name="list_files",
        description="List files in the repository. Shows which files are in the chat session and which are available but not in chat.",
        parameters={
            "type": "object",
            "required": [],
            "properties": {},
        },
        handler=list_files_handler,
    )

    # Read file tool
    def read_file_handler(path: str) -> Dict[str, Any]:
        """Read a file and return its contents."""
        abs_path = commands.coder.abs_root_path(path)
        content = commands.io.read_text(abs_path)

        if content is None:
            return {
                "success": False,
                "path": path,
                "error": "File not found or could not be read",
            }

        return {
            "success": True,
            "path": path,
            "content": content,
        }

    register_tool(
        name="read_file",
        description="Read the contents of a file. Use this to examine code, configuration files, documentation, etc.",
        parameters={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from the repository root",
                }
            },
        },
        handler=read_file_handler,
    )
