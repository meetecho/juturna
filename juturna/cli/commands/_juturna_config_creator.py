import json
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.history import InMemoryHistory

import juturna as jt

from juturna.cli.commands import _create_tools


class PipelineBuilder:
    def __init__(self):
        self._cns = Console()
        self._history = InMemoryHistory()
        self._completer = NodeCompleter(self)

        self._links = dict()
        self._mode = 'base'

        self._registry = _create_tools.discover_nodes()
        self._node_types = sorted(self._registry.keys())

        self._pipeline = {
            'version': jt.__version__,
            'pipeline': {
                'name': '',
                'id': '',
                'folder': '',
                'nodes': [],
                'links': [],
            },
        }

        self._cns.print(
            Panel.fit(
                f'[bold cyan]jt builder ({jt.__version__})[/bold cyan]\n'
                '\n'
                '[dim]> TAB to autocomplete command\n'
                '> ctrl-d or .exit to exit\n'
                '> .help for available commands ',
                border_style='cyan',
            )
        )

        if not self._registry:
            self._cns.print(
                'No nodes found: install juturna-nodes or a package providing '
                'juturna.extensions.nodes or juturna.contrib.<author>.nodes',
                style='yellow',
            )

    def run(self):
        try:
            while True:
                try:
                    if self._mode == 'link':
                        self._handle_link_mode()
                    else:
                        command = prompt(
                            '> ',
                            completer=self._completer,
                            history=self._history,
                            complete_while_typing=True,
                        )

                        if strp_cmd := command.strip():
                            self._execute(strp_cmd)
                except KeyboardInterrupt:
                    if self._mode == 'link':
                        self._mode = 'base'
                        self._links = {}
                        self._cns.print(
                            '\nLink creation cancelled', style='yellow'
                        )
                    else:
                        continue
                except EOFError:
                    self._exit()

                    break
        except KeyboardInterrupt:
            sys.exit(0)

    def _get_base_commands(self) -> list[str]:
        special_cmds = sorted(
            [
                '.exit',
                '.help',
                '.link',
                '.links',
                '.nodes',
                '.save',
            ]
        )
        return self._node_types + special_cmds

    def get_node_references(self) -> list[str]:
        nodes = self._pipeline['pipeline']['nodes']
        names = [node['name'] for node in nodes]
        indices = [str(i) for i in range(len(nodes))]

        return sorted(names) + indices

    def _execute(self, command: str):
        if self._mode == 'base':
            if command.startswith('.'):
                self._execute_special(command)
            elif command in self._registry:
                self._create_node(command)
            else:
                self._cns.print(f'Unknown node type: {command}', style='red')
                self._cns.print(
                    'Use TAB to list the available node types, or .help for '
                    'the command list',
                    style='dim',
                )

    def _execute_special(self, command: str):
        parts = command.split()
        cmd = parts[0]

        if cmd == '.link':
            nodes = self._pipeline['pipeline']['nodes']

            if len(nodes) < 2:
                self._cns.print(
                    'At least 2 nodes required for linking', style='red'
                )

                return

            self._mode = 'link'
            self._links = {}
            self._cns.print('\nLink creation mode', style='bold')
            self._list_nodes()
        elif cmd == '.save':
            self._save()
        elif cmd == '.exit':
            self._exit()
        elif cmd == '.help':
            self._show_help()
        elif cmd == '.nodes':
            self._list_nodes()
        elif cmd == '.links':
            self._list_links()
        else:
            self._cns.print(f'Unknown command: {cmd}', style='red')
            self._cns.print('Use .help to see available commands', style='dim')

    def _create_node(self, node_type: str):
        config = self._registry[node_type]
        origin = config['origin']

        self._cns.print(
            f'\nCreating node: {node_type} [yellow]({origin})[/yellow]',
            style='bold',
        )

        existing_names = [
            n['name'] for n in self._pipeline['pipeline']['nodes']
        ]
        name = prompt(
            'Node name: ',
            validator=Validator.from_callable(
                lambda x: bool(x.strip()) and x.strip() not in existing_names,
                error_message='Name must be unique and non-empty',
            ),
        )

        arguments = config.get('arguments', {})
        node_config = {}

        for arg_name, arg_def in arguments.items():
            default = arg_def.get('default', '')
            help_text = arg_def.get('help', '')

            if help_text:
                self._cns.print(f'{help_text}', style='dim')

            arg_type = arg_def.get('type', 'string')

            value = prompt(
                f'{arg_name} ({arg_type}): ',
                placeholder=FormattedText(
                    [
                        (
                            'class:placeholder',
                            str(default),
                        )
                    ]
                ),
                style=Style.from_dict(
                    {
                        'placeholder': '#888888 italic',
                    }
                ),
            )

            if not value:
                node_config[arg_name] = default

                continue

            try:
                if arg_type == 'boolean':
                    value = value.lower() in ('true', 'yes', '1', 'y')
                elif arg_type == 'integer':
                    value = int(value)
                elif arg_type == 'float':
                    value = float(value)
            except ValueError:
                self._cns.print(
                    f'Warning: Using string for {arg_name}', style='yellow'
                )

            node_config[arg_name] = value

        node = {
            'name': name.strip(),
            'type': node_type,
            'configuration': node_config,
        }

        self._pipeline['pipeline']['nodes'].append(node)
        self._cns.print(f"Node '{name}' added", style='green')

    def _handle_link_mode(self):
        try:
            if 'from' not in self._links:
                source = prompt('Source node: ', completer=self._completer)
                source_name = self._resolve_node_ref(source)

                if not source_name:
                    self._cns.print('Invalid node reference', style='red')
                    self._mode = 'base'
                    self._links = {}

                    return

                self._links['from'] = source_name

            if 'to' not in self._links:
                target = prompt('Target node: ', completer=self._completer)
                target_name = self._resolve_node_ref(target)

                if not target_name:
                    self._cns.print('Invalid node reference', style='red')
                    self._mode = 'base'
                    self._links = {}

                    return

                if target_name == self._links['from']:
                    self._cns.print('Cannot link node to itself', style='red')
                    self._mode = 'base'
                    self._links = {}

                    return

                self._links['to'] = target_name

            link = {
                'from': self._links['from'],
                'to': self._links['to'],
            }

            self._pipeline['pipeline']['links'].append(link)
            f_node = self._links['from']
            t_node = self._links['to']

            self._cns.print(f'Link added: {f_node} -> {t_node}', style='green')
            self._mode = 'base'
            self._links = {}

        except KeyboardInterrupt:
            self._cns.print('\nLink creation cancelled', style='yellow')
            self._mode = 'base'
            self._links = {}

    def _resolve_node_ref(self, ref: str) -> str | None:
        nodes = self._pipeline['pipeline']['nodes']

        if not nodes:
            return None

        try:
            idx = int(ref)

            if 0 <= idx < len(nodes):
                return nodes[idx]['name']
        except ValueError:
            pass

        for node in nodes:
            if node['name'] == ref:
                return ref

        return None

    def _save(self):
        if not self._pipeline['pipeline']['name']:
            self._pipeline['pipeline']['name'] = prompt(
                'Pipeline name: ',
                validator=Validator.from_callable(
                    lambda x: bool(x.strip()),
                    error_message='Name cannot be empty',
                ),
            )

        if not self._pipeline['pipeline']['id']:
            self._pipeline['pipeline']['id'] = prompt(
                'Pipeline ID: ',
                validator=Validator.from_callable(
                    lambda x: bool(x.strip()),
                    error_message='ID cannot be empty',
                ),
            )

        if not self._pipeline['pipeline']['folder']:
            self._pipeline['pipeline']['folder'] = prompt(
                'Pipeline folder: ', default='./pipelines'
            )

        nodes = self._pipeline['pipeline']['nodes']
        links = self._pipeline['pipeline']['links']

        if nodes and not links:
            self._cns.print(
                'Warning: Pipeline has nodes but no links', style='yellow'
            )

            if not confirm('Continue saving? '):
                self._cns.print('Save cancelled', style='yellow')

                return

        default = f'{self._pipeline["pipeline"]["name"]}.json'
        filename = prompt('Filename: ', default=default)

        try:
            with open(filename, 'w') as f:
                json.dump(self._pipeline, f, indent=2)
            self._cns.print(f'Pipeline saved to {filename}', style='green')

            sys.exit(0)
        except Exception as e:
            self._cns.print(f'Save failed: {e}', style='red')
            self._mode = 'base'

    def _exit(self):
        nodes = self._pipeline['pipeline']['nodes']
        links = self._pipeline['pipeline']['links']

        if not nodes and not links:
            sys.exit(0)

        if confirm('Exit without saving? '):
            sys.exit(0)

    def _show_help(self):
        help_text = """
[b cyan]Add node to pipe[/b cyan]:
    <node_type>  Create a node (TAB lists the available types)
                 AudioRtp, extensions.nodes.MyNode, contrib.author.nodes.MyNode

[b cyan]Special Commands[/b cyan]:
    .link     Create a link between nodes
    .save     Save pipeline and exit
    .exit     Exit without saving
    .help     Show this help
    .nodes    List all nodes
    .links    List all links
""".strip()

        self._cns.print(Panel(help_text, title='Commands', border_style='cyan'))

    def _list_nodes(self):
        nodes = self._pipeline['pipeline']['nodes']

        if not nodes:
            self._cns.print('No nodes', style='yellow')

            return

        table = Table()
        table.add_column('Name', style='cyan')
        table.add_column('Type', style='green')
        table.add_column('Origin', style='yellow')
        table.add_column('Config', style='dim')

        for node in nodes:
            config = ', '.join(
                f'{k}={v}' for k, v in node.get('configuration', {}).items()
            )
            table.add_row(
                node['name'],
                node['type'],
                self._registry.get(node['type'], {}).get('origin', 'unknown'),
                config[:40],
            )

        self._cns.print(table)

    def _list_links(self):
        links = self._pipeline['pipeline']['links']
        if not links:
            self._cns.print('No links', style='yellow')

            return

        table = Table()
        table.add_column('Source', style='cyan')
        table.add_column('Destination', style='green')

        print(links)

        for link in links:
            table.add_row(
                link['from'],
                link['to'],
            )

        self._cns.print(table)


class NodeCompleter(Completer):
    def __init__(self, cli):
        self.cli = cli

    def get_completions(self, document, complete_event):
        full_text = document.text_before_cursor.strip()
        word = document.get_word_before_cursor()

        if self.cli._mode == 'link':
            for item in self.cli.get_node_references():
                if item.startswith(word):
                    yield Completion(item, start_position=-len(word))

            return

        if full_text.startswith('.'):
            for item in self.cli._get_base_commands():
                if item.startswith(full_text):
                    yield Completion(item, start_position=-len(full_text))

            return

        # node types can be dotted, so they are matched against the whole input
        # rather than the last word
        for node_type in self.cli._node_types:
            if node_type.startswith(full_text):
                yield Completion(
                    node_type,
                    start_position=-len(full_text),
                    display_meta=f'[{self.cli._registry[node_type]["origin"]}]',
                )
