*FSS* will scan a given directory for matching files and yield results as a generator. You may provide a list of include/exclude rules for files and/or directories. 

The searching is done, asynchronously, from another process. This way, the searching and whatever you're doing with the results may actual run in parallel.

Example::

    import fss.constants
    import fss.config.log
    import fss.orchestrator

    root_path = '/etc'

    filter_rules = [
        (fss.constants.FT_DIR, fss.constants.FILTER_INCLUDE, 'init'),
        (fss.constants.FT_FILE, fss.constants.FILTER_INCLUDE, 'net*'),
        (fss.constants.FT_FILE, fss.constants.FILTER_EXCLUDE, 'networking.conf'),
    ]

    o = fss.orchestrator.Orchestrator(root_path, filter_rules)
    for (entry_type, entry_filepath) in o.recurse():
        if entry_type == fss.constants.FT_DIR:
            print("Directory: [%s]" % (entry_filepath,))
        else: # entry_type == fss.constants.FT_FILE:
            print("File: [%s]" % (entry_filepath,))

Output::

    Directory: [/etc/init]
    File: [/etc/networks]
    File: [/etc/netconfig]
    File: [/etc/init/network-interface-container.conf]
    File: [/etc/init/networking.conf]
    File: [/etc/init/network-interface-security.conf]
    File: [/etc/init/network-interface.conf]

Notice that we include directories named "init" but that we'll still see matching files from the root-path.
