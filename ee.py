#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Rewrites BookOpener.java (which jd-gui mangled into invalid Java) with a
clean, compiling version. Also patches any similar "catch (Exception null)"
or "catch (Throwable null)" that jd-gui may have left elsewhere.

Run from the repo root:

    python fixer.py
    git add -A
    git commit -m "fix: repair BookOpener.java for compilation"
    git push
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


BOOKOPENER_JAVA = r'''package com.yourname.nick.util;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * Legacy book opener kept for source compatibility. The modern
 * implementation lives in VirtualBook; this class simply delegates.
 */
public final class BookOpener {

    private BookOpener() {
    }

    public static ItemStack build(String title, String author, List<String> legacyPages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);
        List<String> clean = new ArrayList<String>();
        for (String p : legacyPages) {
            clean.add((p == null) ? "" : p);
        }
        meta.setPages(clean);
        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    public static void open(Player player, ItemStack book) {
        if (player == null || book == null) {
            return;
        }
        if (VirtualBook.open(player, book)) {
            return;
        }
        ItemStack previous = player.getItemInHand();
        player.setItemInHand(book);
        player.sendMessage(ChatColor.GOLD + "Right-click the book to continue.");
        if (previous != null && previous.getType() != Material.AIR) {
            player.getInventory().addItem(previous);
        }
    }
}
'''


# ---------------------------------------------------------------------------
#  1. replace BookOpener.java with the clean version
# ---------------------------------------------------------------------------

def rewrite_book_opener():
    candidates = [
        os.path.join(ROOT, "src", "main", "java", "com", "yourname", "nick", "util", "BookOpener.java"),
        os.path.join(ROOT, "com", "yourname", "nick", "util", "BookOpener.java"),
    ]
    target = None
    for c in candidates:
        if os.path.isfile(c):
            target = c
            break

    if target is None:
        print("[fixer] BookOpener.java not found - skipping")
        return

    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(BOOKOPENER_JAVA)
    print("[fixer] rewrote " + os.path.relpath(target, ROOT).replace(os.sep, "/"))


# ---------------------------------------------------------------------------
#  2. fix any other "catch (Exception null)" / "catch (Throwable null)"
# ---------------------------------------------------------------------------

CATCH_NULL = re.compile(
    r"catch\s*\(\s*(\w+(?:\.\w+)*)\s+null\s*\)"
)


def fix_catch_null():
    count = 0
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "src")):
        for name in filenames:
            if not name.endswith(".java"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "r", encoding="utf-8") as fh:
                src = fh.read()
            new_src = CATCH_NULL.sub(r"catch (\1 ignored)", src)
            if new_src != src:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(new_src)
                print("[fixer] fixed catch-null in " + name)
                count += 1
    if count == 0:
        print("[fixer] no catch-null patterns found")


# ---------------------------------------------------------------------------
#  3. fix any leftover "() ;" lambda leftovers
# ---------------------------------------------------------------------------

BROKEN_LAMBDA = re.compile(r"\(\s*\)\s*;")


def fix_broken_lambdas():
    count = 0
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "src")):
        for name in filenames:
            if not name.endswith(".java"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "r", encoding="utf-8") as fh:
                src = fh.read()
            # This is intentionally conservative: only flags the exact jd-gui
            # artefact "()," or "();" on its own when preceded by a comma.
            # Real empty lambdas are always inside a longer expression, so
            # this heuristic is safe enough for our purposes.
            if re.search(r",\s*\(\s*\)\s*;", src):
                print("[fixer] WARNING: possible broken lambda in " + name)
                count += 1
    if count == 0:
        print("[fixer] no obvious broken-lambda patterns")


# ---------------------------------------------------------------------------
#  Driver
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" NickSystem - BookOpener fix")
    print("=" * 60)
    rewrite_book_opener()
    fix_catch_null()
    fix_broken_lambdas()
    print("=" * 60)
    print("[fixer] DONE. Now run:")
    print("[fixer]   git add -A")
    print("[fixer]   git commit -m 'fix: repair BookOpener.java'")
    print("[fixer]   git push")
    print("=" * 60)


if __name__ == "__main__":
    main()