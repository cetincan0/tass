from src.constants import READ_ONLY_COMMANDS


def is_read_only_command(command: str) -> bool:
    """A simple check to see if the command is only for reading files.

    Not a comprehensive or foolproof check by any means, and will
    return false negatives to be safe.
    """
    if ">" in command:
        return False

    # Replace everything that potentially runs another command with a pipe
    command = command.replace("&&", "|")
    command = command.replace("||", "|")
    command = command.replace(";", "|")

    pipes = command.split("|")
    for pipe in pipes:
        if pipe.strip().split()[0] not in READ_ONLY_COMMANDS:
            return False

    return True
