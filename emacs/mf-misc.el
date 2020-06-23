
(defconst occur-all-bufregexp "^[~/].*[^/]$")

(defun occur-all (regexp)
  "Shows all lines in all open buffers for REGEXP.  Only buffers
that match files are searched; temporary buffers and dired buffers
are skipped."
  (interactive
   (list (car (occur-read-primary-args))))
  (when regexp
    (occur-1 regexp nil (delq nil
                              (mapcar
                               (lambda (buf)
                                 (when (and
                                        (buffer-file-name buf)
                                        (string-match occur-all-bufregexp (buffer-file-name buf)))
                                   buf))
                               (buffer-list))))))

(provide 'mf-misc)
