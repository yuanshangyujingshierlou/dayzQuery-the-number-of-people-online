# -*- coding: UTF8 -*-
"""winshell - convenience functions to access Windows shell functionality

Certain aspects of the Windows user interface are grouped by
Microsoft as Shell functions. These include the Desktop, shortcut
icons, special folders (such as My Documents) and a few other things.

These are mostly available via the shell module of the win32all
extensions, but whenever I need to use them, I've forgotten the
various constants and so on.

Several of the shell items have two variants: personal and common,
or User and All Users. These refer to systems with profiles in use:
anything from NT upwards, and 9x with Profiles turned on. Where
relevant, the Personal/User version refers to that owned by the
logged-on user and visible only to that user; the Common/All Users
version refers to that maintained by an Administrator and visible
to all users of the system.

Copyright Tim Golden <winshell@timgolden.me.uk> 25th November 2003 - 2012
Licensed under the (GPL-compatible) MIT License:
http://www.opensource.org/licenses/mit-license.php

"""

from __winshell_version__ import __VERSION__

import os, sys
import datetime
import win32con
from win32com import storagecon
from win32com.shell import shell, shellcon
import win32api
import win32timezone
import pythoncom

#
# 2->3 compatibilty workarounds
#
try:
  basestring
except NameError:
  basestring = str
try:
  unicode
except NameError:
  unicode = str
try:
  from collections import namedtuple
  StorageStat = namedtuple (
    "StorageStat",
    ["name", "type", "size", "mtime", "ctime", "atime", "mode", "locks_supported", "clsid", "state_bits", "reserved"]
  )
  make_storage_stat = StorageStat._make
except ImportError:
  make_storage_stat = tuple

class x_winshell (Exception):
  pass

class x_recycle_bin (x_winshell):
  pass

class x_not_found_in_recycle_bin (x_recycle_bin):
  pass

#
# Stolen from winsys
#
def wrapped (fn, *args, **kwargs):
  return fn (*args, **kwargs)

class Unset (object): pass
UNSET = Unset ()

_desktop_folder = shell.SHGetDesktopFolder ()
PyIShellFolder = type (_desktop_folder)

def indented (text, level, indent=2):
  """Take a multiline text and indent it as a block"""
  return "\n".join ("%s%s" % (level * indent * " ", s) for s in text.splitlines ())

def dumped (text, level, indent=2):
  """Put curly brackets round an indented text"""
  return indented ("{\n%s\n}" % indented (text, level+1, indent) or "None", level, indent) + "\n"

def dumped_list (l, level, indent=2):
  return dumped ("\n".join (unicode (i)  for i in l), level, indent)

def dumped_dict (d, level, indent=2):
  return dumped ("\n".join ("%s => %r" % (k, v) for (k, v) in d.items ()), level, indent)

def dumped_flags (f, lookups, level, indent=2):
  return dumped ("\n".join (lookups.names_from_value (f)) or "None", level, indent)

def datetime_from_pytime (pytime):
  if isinstance (pytime, datetime.datetime):
    return pytime
  else:
    return datetime.datetime.fromtimestamp (int (pytime))

#
# Given a namespace (eg a module) and a pattern (eg "FMTID_%s")
# allow a value from within that space to be specified by name
# or by value.
#
def from_constants (namespace, pattern, factory):
  pattern = pattern.lower ()
  def _from_constants (value):
    try:
      return factory (value)
    except (ValueError, TypeError):
      for name in dir (namespace):
        if name.lower () == pattern % value.lower ():
          return getattr (namespace, name)

class WinshellObject (object):

  def __str__ (self):
    return self.as_string ()

  def __repr__ (self):
    return "<%s: %s>" % (self.__class__.__name__, self)

  def as_string (self):
    raise NotImplementedError

  def dumped (self):
    raise NotImplementedError

  def dump (self, level=0):
    sys.stdout.write (self.dumped (level=level))


#
# This was originally a workaround when Win9x didn't implement SHGetFolderPath.
# Now it's just a convenience which supplies the default parameters.
#
def get_path (folder_id):
  return shell.SHGetFolderPath (0, folder_id, None, 0)

def get_folder_by_name (name):
  name = name.upper ()
  if not name.startswith ("CSIDL"):
    name = "CSIDL_" + name
  try:
    return get_path (getattr (shellcon, name))
  except AttributeError:
    raise x_winshell ("No such CSIDL constant %s" % name)

def folder (folder):
  if isinstance (folder, int):
    return get_path (folder)
  else:
    return get_folder_by_name (unicode (folder))

def desktop (common=0):
  "What folder is equivalent to the current desktop?"
  return get_path ((shellcon.CSIDL_DESKTOP, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)[common])

def common_desktop ():
#
# Only here because already used in code
#
  return desktop (common=1)

def application_data (common=0):
  "What folder holds application configuration files?"
  return get_path ((shellcon.CSIDL_APPDATA, shellcon.CSIDL_COMMON_APPDATA)[common])

def favourites (common=0):
  "What folder holds the Explorer favourites shortcuts?"
  return get_path ((shellcon.CSIDL_FAVORITES, shellcon.CSIDL_COMMON_FAVORITES)[common])
bookmarks = favourites

def start_menu (common=0):
  "What folder holds the Start Menu shortcuts?"
  return get_path ((shellcon.CSIDL_STARTMENU, shellcon.CSIDL_COMMON_STARTMENU)[common])

def programs (common=0):
  "What folder holds the Programs shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_PROGRAMS, shellcon.CSIDL_COMMON_PROGRAMS)[common])

def startup (common=0):
  "What folder holds the Startup shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_STARTUP, shellcon.CSIDL_COMMON_STARTUP)[common])

def personal_folder ():
  "What folder holds the My Documents files?"
  return get_path (shellcon.CSIDL_PERSONAL)
my_documents = personal_folder

def recent ():
  "What folder holds the Documents shortcuts (from the Start Menu)?"
  return get_path (shellcon.CSIDL_RECENT)

def sendto ():
  "What folder holds the SendTo shortcuts (from the Context Menu)?"
  return get_path (shellcon.CSIDL_SENDTO)

#
# Internally abstracted function to handle one
#  of several shell-based file manipulation
#  routines. Not all the possible parameters
#  are covered which might be passed to the
#  underlying SHFileOperation API call, but
#  only those which seemed useful to me at
#  the time.
#
def _file_operation (
  operation,
  source_path,
  target_path=None,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  #
  # At present the Python wrapper around SHFileOperation doesn't
  # allow lists of files. Hopefully it will at some point, so
  # take account of it here.
  # If you pass this shell function a "/"-separated path with
  # a wildcard, eg c:/temp/*.tmp, it gets confused. It's ok
  # with a backslash, so convert here.
  #
  source_path = source_path or ""
  if isinstance (source_path, basestring):
    source_path = os.path.abspath (source_path)
  else:
    source_path = [os.path.abspath (i) for i in source_path]

  target_path = target_path or ""
  if isinstance (target_path, basestring):
    target_path = os.path.abspath (target_path)
  else:
    target_path = [os.path.abspath (i) for i in target_path]

  flags = shellcon.FOF_WANTMAPPINGHANDLE
  if allow_undo: flags |= shellcon.FOF_ALLOWUNDO
  if no_confirm: flags |= shellcon.FOF_NOCONFIRMATION
  if rename_on_collision: flags |= shellcon.FOF_RENAMEONCOLLISION
  if silent: flags |= shellcon.FOF_SILENT

  result, n_aborted, mapping = shell.SHFileOperation (
    (hWnd or 0, operation, source_path, target_path, flags, None, None)
  )
  if result != 0:
    raise x_winshell (result)
  elif n_aborted:
    raise x_winshell ("%d operations were aborted by the user" % n_aborted)

  return dict (mapping)

def copy_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file copy. Copying in
  this way allows the possibility of undo, auto-renaming,
  and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
  clobber on a name clash, automatically rename on collision
  and display the animation.
  """
  return _file_operation (
    shellcon.FO_COPY,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def move_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file move. Moving in
  this way allows the possibility of undo, auto-renaming,
  and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
  clobber on a name clash, automatically rename on collision
  and display the animation.
  """
  return _file_operation (
    shellcon.FO_MOVE,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def rename_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file rename. Renaming in
  this way allows the possibility of undo, auto-renaming,
  and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
  clobber on a name clash, automatically rename on collision
  and display the animation.
  """
  return _file_operation (
    shellcon.FO_RENAME,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def delete_file (
  source_path,
  allow_undo=True,
  no_confirm=False,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file delete. Deleting in
  this way uses the system recycle bin, allows the
  possibility of undo, and showing the "flying file"
  animation during the delete.

  The default options allow for undo, don't automatically
  clobber on a name clash and display the animation.
  """
  return _file_operation (
    shellcon.FO_DELETE,
    source_path,
    None,
    allow_undo,
    no_confirm,
    False,
    silent,
    hWnd
  )

class Shortcut (WinshellObject):

  show_states = {
    "normal" : win32con.SW_SHOWNORMAL,
    "max" : win32con.SW_SHOWMAXIMIZED,
    "min" : win32con.SW_SHOWMINIMIZED
  }

  def __init__ (self, lnk_filepath=None, **kwargs):
    self._shell_link = wrapped (
      pythoncom.CoCreateInstance,
      shell.CLSID_ShellLink,
      None,
      pythoncom.CLSCTX_INPROC_SERVER,
      shell.IID_IShellLink
    )
    self.lnk_filepath = lnk_filepath
    if self.lnk_filepath and os.path.exists (self.lnk_filepath):
      wrapped (
        self._shell_link.QueryInterface,
        pythoncom.IID_IPersistFile
      ).Load (
        self.lnk_filepath
      )
    for k, v in kwargs.items ():
      setattr (self, k, v)

  def as_string (self):
    return "%s -> %s" % (self.lnk_filepath or "-unsaved-", self.path or "-no-target-")

  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append ("")
    for attribute, value in sorted (vars (self.__class__).items ()):
      if not attribute.startswith ("_") and isinstance (value, property):
        output.append ("%s: %s" % (attribute, getattr (self, attribute)))
    return dumped ("\n".join (output), level)

  @classmethod
  def from_lnk (cls, lnk_filepath):
    return cls (lnk_filepath)

  @classmethod
  def from_target (cls, target_filepath, lnk_filepath=UNSET, **kwargs):
    target_filepath = os.path.abspath (target_filepath)
    if lnk_filepath is UNSET:
      lnk_filepath = os.path.join (os.getcwd (), os.path.basename (target_filepath) + ".lnk")
    return cls (
      lnk_filepath,
      path=target_filepath,
      **kwargs
    )

  def __enter__ (self):
    return self

  def __exit__ (self, exc_type, exc_val, exc_tb):
    if exc_type is None:
      self.write ()

  def _get_arguments (self):
    return self._shell_link.GetArguments ()
  def _set_arguments (self, arguments):
    self._shell_link.SetArguments (arguments)
  arguments = property (_get_arguments, _set_arguments)

  def _get_description (self):
    return self._shell_link.GetDescription ()
  def _set_description (self, description):
    self._shell_link.SetDescription (description)
  description = property (_get_description, _set_description)

  def _get_hotkey (self):
    return self._shell_link.GetHotkey ()
  def _set_hotkey (self, hotkey):
    self._shell_link.SetHotkey (hotkey)
  hotkey = property (_get_hotkey, _set_hotkey)

  def _get_icon_location (self):
    path, index = self._shell_link.GetIconLocation ()
    return path, index
  def _set_icon_location (self, icon_location):
    self._shell_link.SetIconLocation (*icon_location)
  icon_location = property (_get_icon_location, _set_icon_location)

  def _get_path (self):
    lnk_filepath, data = self._shell_link.GetPath (shell.SLGP_UNCPRIORITY)
    return lnk_filepath
  def _set_path (self, path):
    self._shell_link.SetPath (path)
  path = property (_get_path, _set_path)

  def _get_show_cmd (self):
    show_cmd = self._shell_link.GetShowCmd ()
    for k, v in self.show_states.items ():
      if v == show_cmd:
        return k
    else:
      return None
  def _set_show_cmd (self, show_cmd):
    try:
      show_cmd = int (show_cmd)
    except ValueError:
      show_cmd = self.show_states[show_cmd]
    self._shell_link.SetShowCmd (show_cmd)
  show_cmd = property (_get_show_cmd, _set_show_cmd)

  def _get_working_directory (self):
    return self._shell_link.GetWorkingDirectory ()
  def _set_working_directory (self, working_directory):
    self._shell_link.SetWorkingDirectory (working_directory)
  working_directory = property (_get_working_directory, _set_working_directory)

  def write (self, lnk_filepath=None):
    if not lnk_filepath:
      lnk_filepath = self.lnk_filepath
    if lnk_filepath is None:
      raise x_shell (errmsg="Must specify a lnk_filepath for an unsaved shortcut")

    ipersistfile = wrapped (
      self._shell_link.QueryInterface,
      pythoncom.IID_IPersistFile
    ).Save (
      lnk_filepath,
      lnk_filepath == self.lnk_filepath
    )

    self.lnk_filepath = lnk_filepath
    return self

def shortcut (source=UNSET):
  if source is None:
    return None
  elif source is UNSET:
    return Shortcut ()
  elif isinstance (source, Shortcut):
    return source
  elif source.endswith (".lnk"):
    return Shortcut.from_lnk (source)
  else:
    return Shortcut.from_target (source)

#
# Constants for structured storage
#
# These come from ObjIdl.h
FMTID_USER_DEFINED_PROPERTIES = "{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"
FMTID_CUSTOM_DEFINED_PROPERTIES = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

PIDSI_TITLE               = 0x00000002
PIDSI_SUBJECT             = 0x00000003
PIDSI_AUTHOR              = 0x00000004
PIDSI_CREATE_DTM          = 0x0000000c
PIDSI_KEYWORDS            = 0x00000005
PIDSI_COMMENTS            = 0x00000006
PIDSI_TEMPLATE            = 0x00000007
PIDSI_LASTAUTHOR          = 0x00000008
PIDSI_REVNUMBER           = 0x00000009
PIDSI_EDITTIME            = 0x0000000a
PIDSI_LASTPRINTED         = 0x0000000b
PIDSI_LASTSAVE_DTM        = 0x0000000d
PIDSI_PAGECOUNT           = 0x0000000e
PIDSI_WORDCOUNT           = 0x0000000f
PIDSI_CHARCOUNT           = 0x00000010
PIDSI_THUMBNAIL           = 0x00000011
PIDSI_APPNAME             = 0x00000012
PROPERTIES = (
  PIDSI_TITLE,
  PIDSI_SUBJECT,
  PIDSI_AUTHOR,
  PIDSI_CREATE_DTM,
  PIDSI_KEYWORDS,
  PIDSI_COMMENTS,
  PIDSI_TEMPLATE,
  PIDSI_LASTAUTHOR,
  PIDSI_EDITTIME,
  PIDSI_LASTPRINTED,
  PIDSI_LASTSAVE_DTM,
  PIDSI_PAGECOUNT,
  PIDSI_WORDCOUNT,
  PIDSI_CHARCOUNT,
  PIDSI_APPNAME
)

#
# This was taken from someone else's example, but I can't find where.
# If you know, please tell me so I can give due credit.
#
def structured_storage (filename):
  """Pick out info from MS documents with embedded
   structured storage (typically MS Word docs etc.)

  Returns a dictionary of information found
  """

  if not pythoncom.StgIsStorageFile (filename):
    return {}

  flags = storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE
  storage = pythoncom.StgOpenStorage (filename, None, flags)
  try:
    properties_storage = storage.QueryInterface (pythoncom.IID_IPropertySetStorage)
  except pythoncom.com_error:
    return {}

  property_sheet = properties_storage.Open (FMTID_USER_DEFINED_PROPERTIES)
  try:
    data = property_sheet.ReadMultiple (PROPERTIES)
  finally:
    property_sheet = None

  title, subject, author, created_on, keywords, comments, template_used, \
   updated_by, edited_on, printed_on, saved_on, \
   n_pages, n_words, n_characters, \
   application = data

  result = {}
  if title: result['title'] = title
  if subject: result['subject'] = subject
  if author: result['author'] = author
  if created_on: result['created_on'] = created_on
  if keywords: result['keywords'] = keywords
  if comments: result['comments'] = comments
  if template_used: result['template_used'] = template_used
  if updated_by: result['updated_by'] = updated_by
  if edited_on: result['edited_on'] = edited_on
  if printed_on: result['printed_on'] = printed_on
  if saved_on: result['saved_on'] = saved_on
  if n_pages: result['n_pages'] = n_pages
  if n_words: result['n_words'] = n_words
  if n_characters: result['n_characters'] = n_characters
  if application: result['application'] = application
  return result

class ShellItem (WinshellObject):

  def __init__ (self, parent, pidl):
    #
    # parent is a PyIShellFolder object (or something similar)
    # pidl is a PyIDL object (basically: a list of SHITEMs)
    #
    assert parent is None or isinstance (parent, ShellFolder), "parent is %r" % parent
    self.parent = parent
    self.pidl = pidl

  @classmethod
  def from_pidl (cls, pidl, parent_obj=None):
    if parent_obj is None:
      #
      # pidl is absolute
      #
      parent_obj = _desktop.BindToObject (pidl[:-1], None, shell.IID_IShellFolder)
      rpidl = pidl[-1:]
    else:
      #
      # pidl is relative
      #
      rpidl = pidl
    return cls (parent_obj, rpidl)

  @classmethod
  def from_path (cls, path):
    _, pidl, flags = _desktop.ParseDisplayName (0, None, path, shellcon.SFGAO_FOLDER)
    if flags & shellcon.SFGAO_FOLDER:
      return ShellFolder.from_pidl (pidl)
    else:
      return ShellItem.from_pidl (pidl)

  def as_string (self):
    return self.name ()

  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append ("")
    output.append (dumped_list (self.attributes (), level))
    return dumped ("\n".join (output), level)

  def attributes (self):
    prefix = "SFGAO_"
    results = set ()
    all_attributes = self.parent._folder.GetAttributesOf ([self.pidl], -1)
    for attr in dir (shellcon):
      if attr.startswith (prefix):
        if all_attributes & getattr (shellcon, attr):
          results.add (attr[len (prefix):].lower ())
    return results

  def attribute (self, attributes):
    try:
      attribute = int (attributes)
    except ValueError:
      attribute = getattr (shellcon, "SFGAO_" + attributes.upper ())
    except TypeError:
      attribute = 0
      for a in attributes:
        try:
          attribute = attribute | a
        except TypeError:
          attribute = attribute | getattr (shellcon, "SFGAO_" + a.upper ())

    return bool (self.parent._folder.GetAttributesOf ([self.pidl], attribute) & attribute)

  def filename (self):
    return self.name (shellcon.SHGDN_FORPARSING)

  def name (self, type=shellcon.SHGDN_NORMAL):
    return self.parent._folder.GetDisplayNameOf (self.pidl, type)

  def stat (self):
    stream = self.parent._folder.BindToStorage (self.pidl, None, pythoncom.IID_IStream)
    return make_storage_stat (stream.Stat ())

  def getsize (self):
    return self.stat ()[2]

  def getmtime (self):
    return datetime_from_pytime (self.stat ()[3])

  def getctime (self):
    return self.stat ()[4]

  def getatime (self):
    return self.stat ()[5]

  def detail (self, fmtid, pid):
    folder2 = self.parent._folder.QueryInterface (shell.IID_IShellFolder2)
    return folder2.GetDetailsEx (self.pidl, (fmtid, pid))

class ShellFolder (ShellItem):

  def __init__ (self, parent, pidl):
    ShellItem.__init__ (self, parent, pidl)
    if parent:
      self._folder = self.parent._folder.BindToObject (self.pidl, None, shell.IID_IShellFolder)
    else:
      self._folder = None

  def __getitem__ (self, item):
    return self.get_child (item)

  def folders (self, flags=0):
    enum = self._folder.EnumObjects (0, flags | shellcon.SHCONTF_FOLDERS)
    if enum:
      while True:
        pidls = enum.Next (1)
        if pidls:
          for pidl in pidls:
            yield self.folder_factory (pidl)
        else:
          break

  def items (self, flags=0):
    enum = self._folder.EnumObjects (0, flags | shellcon.SHCONTF_NONFOLDERS)
    if enum:
      while True:
        pidls = enum.Next (1)
        if pidls:
          for pidl in pidls:
            yield self.item_factory (pidl)
        else:
          break

  def enumerate (self, flags=0):
    for folder in self.folders (flags):
      yield folder
    for item in self.items (flags):
      yield item
  __iter__ = enumerate

  def walk (self, flags=0):
    folders = list (self.folders (flags))
    items = list (self.items (flags))
    yield self, folders, items
    for folder in folders:
      for result in folder.walk (flags):
        yield result

  def folder_factory (self, pidl):
    return ShellFolder (self, pidl)

  def item_factory (self, pidl):
    return ShellItem (self, pidl)

  def get_child (self, name, hWnd=None):
    n_eaten, pidl, attributes = self._folder.ParseDisplayName (hWnd, None, name, shellcon.SFGAO_FOLDER)
    if attributes & shellcon.SFGAO_FOLDER:
      return self.folder_factory (pidl)
    else:
      return self.item_factory (pidl)

class ShellRecycledItem (ShellItem):

  PID_DISPLACED_FROM = 2 # Location that file was deleted from.
  PID_DISPLACED_DATE = 3 # Date that the file was deleted.

  def as_string (self):
    return "%s recycled at %s" % (self.original_filename (), self.recycle_date ())

  def original_filename (self):
    return os.path.join (
      self.detail (shell.FMTID_Displaced, self.PID_DISPLACED_FROM) ,
      self.name (shellcon.SHGDN_INFOLDER)
    )

  def recycle_date (self):
    return datetime_from_pytime (self.detail (shell.FMTID_Displaced, self.PID_DISPLACED_DATE))

  def real_filename (self):
    return self.parent._folder.GetDisplayNameOf (self.pidl, shellcon.SHGDN_FORPARSING)

  def undelete (self):
    return move_file (self.real_filename (), self.original_filename (), rename_on_collision=True)

  def contents (self, buffer_size=8192):
    istream = self.parent._folder.BindToStorage (self.pidl, None, pythoncom.IID_IStream)
    while True:
      contents = istream.Read (buffer_size)
      if contents:
        yield contents
      else:
        break

class ShellRecycleBin (ShellFolder):
  """Wrap the shell object which represents the union of all the
  recycle bins on this system.
  """

  def __init__ (self):
    ShellFolder.__init__ (
      self,
      ShellDesktop (),
      shell.SHGetSpecialFolderLocation (0, shellcon.CSIDL_BITBUCKET)
    )

  def item_factory (self, pidl):
    return ShellRecycledItem (self, pidl)
  folder_factory = item_factory

  @staticmethod
  def empty (confirm=True, show_progress=True, sound=True):
    flags = 0
    if not confirm: flags |= shellcon.SHERB_NOCONFIRMATION
    if not show_progress: flags |= shellcon.SHERB_NOPROGRESSUI
    if not sound: flags |= shellcon.SHERB_NOSOUND
    shell.SHEmptyRecycleBin (None, None, flags)

  def undelete (self, original_filepath):
    """Restore the most recent version of a filepath, returning
    the filepath it was restored to (as rename-on-collision will
    apply if a file already exists at that path).
    """
    candidates = self.versions (original_filepath)
    if not candidates:
      raise x_not_found_in_recycle_bin ("%s not found in the Recycle Bin" % original_filepath)
    newest = sorted (candidates, key=lambda entry: entry.recycle_date ())[-1]
    ostensible_copy_target = os.path.join (
      os.path.dirname (original_filepath),
      os.path.basename (newest.real_filename ())
    ).lower ()
    for remapped_from, remapped_to in newest.undelete ().items ():
      if remapped_from.lower () == ostensible_copy_target:
        return remapped_to
    else:
      return original_filepath

  def versions (self, original_filepath):
    original_filepath = original_filepath.lower ()
    return [entry for entry in self if entry.original_filename ().lower () == original_filepath]

def recycle_bin ():
  """Return an object representing all the recycle bins on the
  system.
  """
  return ShellRecycleBin ()

def undelete (filepath):
  return recycle_bin ().undelete (filepath)

class ShellDesktop (ShellFolder):

  def __init__ (self):
    ShellFolder.__init__ (self, None, [])
    self._folder = _desktop_folder

  def name (self, type=shellcon.SHGDN_NORMAL):
    return self._folder.GetDisplayNameOf (self.pidl, type)

def shell_object (shell_object=UNSET):
  if shell_object is None:
    return None
  elif shell_object is UNSET:
    return ShellDesktop ()
  elif isinstance (shell_object, ShellItem):
    return shell_object
  else:
    return ShellDesktop ().get_child (shell_object)

#
# Legacy functions, retained for backwards compatibility
#

def CreateShortcut (Path, Target, Arguments = "", StartIn = "", Icon = ("", 0), Description = ""):
  """Create a Windows shortcut:

  Path - As what file should the shortcut be created?
  Target - What command should the desktop use?
  Arguments - What arguments should be supplied to the command?
  StartIn - What folder should the command start in?
  Icon - (filename, index) What icon should be used for the shortcut?
  Description - What description should the shortcut be given?

  eg
  CreateShortcut (
    Path=os.path.join (desktop (), "PythonI.lnk"),
    Target=r"c:\python\python.exe",
    Icon=(r"c:\python\python.exe", 0),
    Description="Python Interpreter"
  )
  """
  lnk = shortcut (Target)
  lnk.arguments = Arguments
  lnk.working_directory = StartIn
  lnk.icon_location = Icon
  lnk.description = Description
  lnk.write (Path)


if __name__ == '__main__':
  try:
    raw_input
  except NameError:
    raw_input = input
  try:
    print ('Desktop =>', desktop ())
    print ('Common Desktop =>', desktop (1))
    print ('Application Data =>', application_data ())
    print ('Common Application Data =>', application_data (1))
    print ('Bookmarks =>', bookmarks ())
    print ('Common Bookmarks =>', bookmarks (1))
    print ('Start Menu =>', start_menu ())
    print ('Common Start Menu =>', start_menu (1))
    print ('Programs =>', programs ())
    print ('Common Programs =>', programs (1))
    print ('Startup =>', startup ())
    print ('Common Startup =>', startup (1))
    print ('My Documents =>', my_documents ())
    print ('Recent =>', recent ())
    print ('SendTo =>', sendto ())
  finally:
    raw_input ("Press enter...")
