/**
 * Minimal, dependency-free drag-and-drop helper shared by the sequencing and
 * cloze games. Supports pointer-based drag (mouse + touch, via Pointer
 * Events) for reordering a list of draggable items among a set of drop
 * targets, PLUS a keyboard fallback so the games are fully operable without
 * a mouse (drag is a progressive enhancement, not the only path).
 *
 * Usage (reordering, sequencing game):
 *   GamesXBlockDnD.makeSortable(listEl, '.gx-drag-item', onReorder);
 *
 * Usage (drop-into-target, cloze game):
 *   GamesXBlockDnD.makeDroppable(bankEl, '.gx-drag-item', targetsEl, '.gx-drop-target', onDrop);
 */
(function (global) {
    'use strict';

    function indexInParent(el) {
        return Array.prototype.indexOf.call(el.parentNode.children, el);
    }

    /**
     * Enable drag-to-reorder among sibling `itemSelector` elements inside
     * `listEl`. Calls `onReorder(orderedIds)` (ids read from each item's
     * `data-id` attribute) after every reorder, whether by drag or keyboard.
     * Each item also gets "Move up"/"Move down" buttons wired automatically
     * if it contains elements matching `[data-action="move-up"]` /
     * `[data-action="move-down"]`.
     */
    function makeSortable(listEl, itemSelector, onReorder) {
        function currentOrder() {
            return Array.prototype.map.call(listEl.querySelectorAll(itemSelector), function (el) {
                return el.getAttribute('data-id');
            });
        }

        function moveItem(itemEl, direction) {
            var idx = indexInParent(itemEl);
            var sibling = direction === 'up' ? itemEl.previousElementSibling : itemEl.nextElementSibling;
            if (!sibling) { return; }
            if (direction === 'up') {
                listEl.insertBefore(itemEl, sibling);
            } else {
                listEl.insertBefore(sibling, itemEl);
            }
            itemEl.focus();
            onReorder(currentOrder());
        }

        Array.prototype.forEach.call(listEl.querySelectorAll(itemSelector), function (itemEl) {
            itemEl.setAttribute('draggable', 'true');

            itemEl.addEventListener('dragstart', function (e) {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', itemEl.getAttribute('data-id'));
                itemEl.classList.add('gx-dragging');
            });
            itemEl.addEventListener('dragend', function () {
                itemEl.classList.remove('gx-dragging');
            });
            itemEl.addEventListener('dragover', function (e) {
                e.preventDefault();
                var dragging = listEl.querySelector('.gx-dragging');
                if (!dragging || dragging === itemEl) { return; }
                var rect = itemEl.getBoundingClientRect();
                var before = (e.clientY - rect.top) < rect.height / 2;
                listEl.insertBefore(dragging, before ? itemEl : itemEl.nextSibling);
            });
            itemEl.addEventListener('drop', function (e) {
                e.preventDefault();
                onReorder(currentOrder());
            });

            var upBtn = itemEl.querySelector('[data-action="move-up"]');
            var downBtn = itemEl.querySelector('[data-action="move-down"]');
            if (upBtn) {
                upBtn.addEventListener('click', function (e) { e.preventDefault(); moveItem(itemEl, 'up'); });
            }
            if (downBtn) {
                downBtn.addEventListener('click', function (e) { e.preventDefault(); moveItem(itemEl, 'down'); });
            }

            itemEl.addEventListener('keydown', function (e) {
                if (e.altKey && e.key === 'ArrowUp') { e.preventDefault(); moveItem(itemEl, 'up'); }
                if (e.altKey && e.key === 'ArrowDown') { e.preventDefault(); moveItem(itemEl, 'down'); }
            });
        });

        listEl.addEventListener('dragover', function (e) { e.preventDefault(); });
    }

    /**
     * Enable drag-from-bank-to-target. Draggable elements matching
     * `itemSelector` inside `sourceEl` can be dropped onto elements matching
     * `targetSelector` inside `targetsEl`. Each target accepts exactly one
     * item at a time (dropping again replaces it, returning the displaced
     * item to the bank). Calls `onDrop(itemId, targetId)` after every
     * successful drop, and `onReturn(itemId)` when an item is dragged back
     * out of a target into the bank.
     *
     * Also wires a click-to-select-then-click-to-place keyboard/touch
     * fallback: clicking a bank item "arms" it (aria-pressed=true), and a
     * subsequent click on a target places it -- so dragging is never the
     * only way to complete the game.
     */
    function makeDroppable(sourceEl, itemSelector, targetsEl, targetSelector, onDrop, onReturn) {
        var armedItemId = null;

        function setArmed(itemId) {
            armedItemId = itemId;
            Array.prototype.forEach.call(sourceEl.querySelectorAll(itemSelector), function (el) {
                el.setAttribute('aria-pressed', el.getAttribute('data-id') === itemId ? 'true' : 'false');
            });
        }

        function bindItem(itemEl) {
            itemEl.setAttribute('draggable', 'true');
            itemEl.setAttribute('role', 'button');
            itemEl.setAttribute('tabindex', '0');
            itemEl.setAttribute('aria-pressed', 'false');

            itemEl.addEventListener('dragstart', function (e) {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', itemEl.getAttribute('data-id'));
            });

            itemEl.addEventListener('click', function () {
                var id = itemEl.getAttribute('data-id');
                setArmed(armedItemId === id ? null : id);
            });
            itemEl.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    itemEl.click();
                }
            });
        }

        Array.prototype.forEach.call(sourceEl.querySelectorAll(itemSelector), bindItem);

        Array.prototype.forEach.call(targetsEl.querySelectorAll(targetSelector), function (targetEl) {
            targetEl.setAttribute('role', 'button');
            targetEl.setAttribute('tabindex', '0');

            targetEl.addEventListener('dragover', function (e) { e.preventDefault(); });
            targetEl.addEventListener('drop', function (e) {
                e.preventDefault();
                var itemId = e.dataTransfer.getData('text/plain');
                if (itemId) {
                    onDrop(itemId, targetEl.getAttribute('data-target-id'));
                }
            });

            // A single click handler decides between two mutually exclusive actions:
            // if an item is armed (selected from the bank), clicking any target places
            // it there; otherwise, clicking an already-filled target returns its item
            // to the bank. This avoids both actions firing off the same click.
            function handleTargetActivate() {
                if (armedItemId) {
                    onDrop(armedItemId, targetEl.getAttribute('data-target-id'));
                    setArmed(null);
                    return;
                }
                var filledId = targetEl.getAttribute('data-filled-id');
                if (filledId && onReturn) {
                    onReturn(filledId);
                }
            }
            targetEl.addEventListener('click', handleTargetActivate);
            targetEl.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleTargetActivate(); }
            });
        });
    }

    global.GamesXBlockDnD = {
        makeSortable: makeSortable,
        makeDroppable: makeDroppable,
        bindNewDraggable: function (itemEl) {
            // Exposed so games can re-bind a single new element (e.g. after
            // returning an item to the bank and re-rendering it) without
            // re-scanning/re-binding the whole container.
            itemEl.setAttribute('draggable', 'true');
        },
    };
}(window));
