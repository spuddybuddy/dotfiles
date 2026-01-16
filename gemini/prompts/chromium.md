*Removing a commandline flag*

To remove a commandline flag named FLAG from Chromium, perform the following
steps in order:

1 Read the documentation at the top of chrome/browser/flag-metadata.json and chrome/browser/flag_descriptions.h.

2 Find the matching entry for FLAG in chrome/browser/flag-metadata.json and remove it.  Remember the email addresses that were listed as owners for the flag entry. 

3 Find the corresponding flag definition in about_flags.cc and remove it.

4 Find the corresponding flag description strings in chrome/browser/flag_descriptions.h and remove them.

5 Compile the `chrome` target with all of these changes and verify that there are no compliation errors.

6 Upload a CL with these changes and set as reviewers the owners of the flag noted in step 2.


