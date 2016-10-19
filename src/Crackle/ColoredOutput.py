__author__ = 'shahab'

colors = {
    'white':        "\033[1;37m",
    'yellow':       "\033[1;33m",
    'green':        "\033[1;32m",
    'blue':         "\033[1;34m",
    'cyan':         "\033[1;36m",
    'red':          "\033[1;31m",
    'magenta':      "\033[1;35m",
    'black':        "\033[1;30m",
    'darkwhite':    "\033[0;37m",
    'darkyellow':   "\033[0;33m",
    'darkgreen':    "\033[0;32m",
    'darkblue':     "\033[0;34m",
    'darkcyan':     "\033[0;36m",
    'darkred':      "\033[0;31m",
    'darkmagenta':  "\033[0;35m",
    'darkblack':    "\033[0;30m",
    'off':          "\033[0;0m"
}


def make_colored(color, string):
    """
    This function is useful to output information to the stdout by exploiting different colors, depending on the
    result of the last command executed.

    It is possible to chose one of the following colors:
        - white
        - yellow
        - green
        - blue
        - cyan
        - red
        - magenta
        - black
        - darkwhite
        - darkyellow
        - darkgreen
        - darkblue
        - darkcyan
        - darkred
        - darkmagenta
        - darkblack
        - off

    :param color: The color of the output string, chosen from the previous list.
    :param string: The string to color
    :return: The colored string if the color is valid, the original string otherwise.
    """

    try:
        return colors[color] + string + colors['off']
    except:
        return string


