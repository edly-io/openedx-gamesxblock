/* Word search: drag across cells (or click start cell then end cell) to
 * select a straight line; if it matches a hidden word, it's marked found.
 * Ungraded -- tracks completion + best time only. */
function GamesXBlockWordSearch(runtime, element) {
    'use strict';

    var gridEl = $('#gx-wordsearch-grid', element)[0];
    if (!gridEl) { return; } // no words configured

    var wordListEl = $('#gx-wordsearch-word-list', element)[0];
    var bannerEl = $('#gx-wordsearch-banner', element)[0];
    var announceEl = $('#gx-wordsearch-announce', element)[0];
    var timerEl = $('#gx-wordsearch-timer', element)[0];
    var completeUrl = runtime.handlerUrl(element, 'complete_wordsearch');

    // wordKey (e.g. "0-0,0-1,0-2") -> { word, found }
    var wordsByKey = {};
    var remainingCount = 0;
    Array.prototype.forEach.call(wordListEl.querySelectorAll('li'), function (li) {
        var key = li.getAttribute('data-cells');
        wordsByKey[key] = { word: li.getAttribute('data-word'), el: li, found: false };
        remainingCount += 1;
    });

    var startCell = null;
    var selecting = false;
    var startTime = Date.now();
    var timerInterval = null;

    if (timerEl) {
        timerInterval = setInterval(function () {
            var elapsed = Math.floor((Date.now() - startTime) / 1000);
            var mins = Math.floor(elapsed / 60);
            var secs = elapsed % 60;
            timerEl.textContent = mins + ':' + (secs < 10 ? '0' : '') + secs;
        }, 1000);
    }

    function announce(message) {
        if (!announceEl) { return; }
        announceEl.textContent = '';
        void announceEl.offsetHeight;
        announceEl.textContent = message;
    }

    function cellsBetween(a, b) {
        var dr = Math.sign(b.row - a.row);
        var dc = Math.sign(b.col - a.col);
        var steps = Math.max(Math.abs(b.row - a.row), Math.abs(b.col - a.col));
        // Only allow straight lines: horizontal, vertical, or perfect diagonal.
        if (Math.abs(b.row - a.row) !== 0 && Math.abs(b.col - a.col) !== 0 &&
            Math.abs(b.row - a.row) !== Math.abs(b.col - a.col)) {
            return null;
        }
        var cells = [];
        for (var i = 0; i <= steps; i++) {
            cells.push({ row: a.row + dr * i, col: a.col + dc * i });
        }
        return cells;
    }

    function cellKey(cells) {
        return cells.map(function (c) { return c.row + '-' + c.col; }).join(',');
    }

    function reversedKey(key) {
        return key.split(',').reverse().join(',');
    }

    function clearHighlight() {
        Array.prototype.forEach.call(gridEl.querySelectorAll('.gx-selecting'), function (el) {
            el.classList.remove('gx-selecting');
        });
    }

    function highlight(cells) {
        clearHighlight();
        cells.forEach(function (c) {
            var cellEl = gridEl.querySelector('[data-row="' + c.row + '"][data-col="' + c.col + '"]');
            if (cellEl) { cellEl.classList.add('gx-selecting'); }
        });
    }

    function markFound(cells) {
        cells.forEach(function (c) {
            var cellEl = gridEl.querySelector('[data-row="' + c.row + '"][data-col="' + c.col + '"]');
            if (cellEl) { cellEl.classList.add('gx-found'); }
        });
    }

    function checkSelection(a, b) {
        var cells = cellsBetween(a, b);
        if (!cells) { return; }
        var key = cellKey(cells);
        var revKey = reversedKey(key);
        var entry = wordsByKey[key] || wordsByKey[revKey];
        if (entry && !entry.found) {
            entry.found = true;
            markFound(cells);
            entry.el.classList.add('gx-found');
            remainingCount -= 1;
            announce(entry.word + ' found!');
            if (remainingCount === 0) {
                finish();
            }
        }
    }

    function cellFromEvent(e) {
        var target = e.target.closest ? e.target.closest('.gx-wordsearch-cell') : null;
        if (!target) { return null; }
        return { row: parseInt(target.getAttribute('data-row'), 10), col: parseInt(target.getAttribute('data-col'), 10) };
    }

    gridEl.addEventListener('pointerdown', function (e) {
        var cell = cellFromEvent(e);
        if (!cell) { return; }
        startCell = cell;
        selecting = true;
        highlight([cell]);
    });
    gridEl.addEventListener('pointermove', function (e) {
        if (!selecting || !startCell) { return; }
        var cell = cellFromEvent(e);
        if (!cell) { return; }
        var cells = cellsBetween(startCell, cell);
        if (cells) { highlight(cells); }
    });
    gridEl.addEventListener('pointerup', function (e) {
        if (!selecting || !startCell) { return; }
        var cell = cellFromEvent(e);
        selecting = false;
        clearHighlight();
        if (cell) { checkSelection(startCell, cell); }
        startCell = null;
    });

    function finish() {
        if (timerInterval) { clearInterval(timerInterval); }
        var elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        bannerEl.textContent = 'You found every word!';
        bannerEl.className = 'gx-status-banner gx-visible gx-banner-success';
        announce('Congratulations, you found every word!');

        $.ajax({
            type: 'POST',
            url: completeUrl,
            data: JSON.stringify({ time_seconds: elapsedSeconds }),
            contentType: 'application/json',
            dataType: 'json',
            success: function (response) {
                if (response.is_new_best) {
                    bannerEl.textContent += ' New best time: ' + response.best_time_seconds + 's';
                }
            },
        });
    }
}
