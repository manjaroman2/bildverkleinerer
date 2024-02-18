from threading import currentThread
from sys import __stdout__, __stderr__, stdout, stderr
from io import StringIO
from werkzeug import local

# Save all of the objects for use later.
orig___stdout__ = __stdout__
orig___stderr__ = __stderr__
orig_stdout = stdout
orig_stderr = stderr
thread_proxies = {}
proxy_enabled = False


def redirect() -> StringIO:
    """
    Enables the redirect for the current thread's output to a single io
    object and returns the object.

    :return: The StringIO object.
    :rtype: ``io.StringIO``
    """
    # Get the current thread's identity.
    ident = currentThread().ident

    # Enable the redirect and return the io object.
    thread_proxies[ident] = StringIO()
    return thread_proxies[ident]


def stop_redirect() -> str:
    """
    Enables the redirect for the current thread's output to a single io
    object and returns the object.

    :return: The final string value.
    :rtype: ``str``
    """
    # Get the current thread's identity.
    ident = currentThread().ident

    # Only act on proxied threads.
    if ident not in thread_proxies:
        return

    # Read the value, close/remove the buffer, and return the value.
    retval = thread_proxies[ident].getvalue()
    thread_proxies[ident].close()
    del thread_proxies[ident]
    return retval


def _get_stream(original):
    """
    Returns the inner function for use in the LocalProxy object.

    :param original: The stream to be returned if thread is not proxied.
    :type original: ``file``
    :return: The inner function for use in the LocalProxy object.
    :rtype: ``function``
    """

    def proxy():
        """
        Returns the original stream if the current thread is not proxied,
        otherwise we return the proxied item.

        :return: The stream object for the current thread.
        :rtype: ``file``
        """
        # Get the current thread's identity.
        ident = currentThread().ident

        # Return the proxy, otherwise return the original.
        return thread_proxies.get(ident, original)

    # Return the inner function.
    return proxy


def enable_proxy():
    """
    Overwrites __stdout__, __stderr__, stdout, and stderr with the proxied
    objects.
    """
    __stdout__ = local.LocalProxy(_get_stream(__stdout__))
    __stderr__ = local.LocalProxy(_get_stream(__stderr__))
    stdout = local.LocalProxy(_get_stream(stdout))
    stderr = local.LocalProxy(_get_stream(stderr))
    proxy_enabled = True


def disable_proxy():
    """
    Overwrites __stdout__, __stderr__, stdout, and stderr with the original
    objects.
    """
    __stdout__ = orig___stdout__
    __stderr__ = orig___stderr__
    stdout = orig_stdout
    stderr = orig_stderr
    proxy_enabled = False
