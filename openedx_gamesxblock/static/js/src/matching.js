/* Matching game: click a term then a definition to connect them with an
 * arrow line. Correctness is intentionally hidden until Submit -- clicking
 * only ever shows a neutral "connected" line, never right/wrong feedback. */
function GamesXBlockMatching(runtime, element) {
    'use strict';

    var board = $('#gx-matching-board', element)[0];
    if (!board) { return; } // no pairs configured

    var connector = new window.GamesXBlockArrowConnector(board);
    var announceEl = $('#gx-matching-announce', element)[0];
    var submitBtn = $('#gx-matching-submit', element)[0];
    var resetBtn = $('#gx-matching-reset', element)[0];
    var progressEl = $('#gx-matching-progress', element)[0];
    var bannerEl = $('#gx-matching-banner', element)[0];

    var termBoxes = Array.prototype.slice.call(board.querySelectorAll('[data-side="term"]'));
    var defBoxes = Array.prototype.slice.call(board.querySelectorAll('[data-side="definition"]'));
    var defByTag = {};
    defBoxes.forEach(function (el) { defByTag[el.getAttribute('data-tag')] = el; });
    var termByCardId = {};
    termBoxes.forEach(function (el) { termByCardId[el.getAttribute('data-card-id')] = el; });

    // connections: cardId (term) -> tag (definition). One entry per connected term.
    var connections = {};
    var selectedTerm = null;
    var selectedDef = null;
    var locked = false;
    var submitUrl = runtime.handlerUrl(element, 'submit_matching');

    function announce(message) {
        if (!announceEl) { return; }
        announceEl.textContent = '';
        void announceEl.offsetHeight;
        announceEl.textContent = message;
    }

    function updateProgress() {
        var connectedCount = Object.keys(connections).length;
        progressEl.textContent = connectedCount + ' / ' + termBoxes.length + ' connected';
        submitBtn.disabled = locked || connectedCount !== termBoxes.length;
    }

    function clearSelectionStyles() {
        if (selectedTerm) { selectedTerm.classList.remove('gx-selected'); }
        if (selectedDef) { selectedDef.classList.remove('gx-selected'); }
        selectedTerm = null;
        selectedDef = null;
    }

    function connect(termEl, defEl) {
        var cardId = termEl.getAttribute('data-card-id');
        var tag = defEl.getAttribute('data-tag');

        // A term/definition can only be in one connection at a time -- replacing
        // an existing one first tears down its old line.
        if (connections[cardId]) {
            connector.remove(cardId);
        }
        connections[cardId] = tag;
        termEl.classList.add('gx-connected');
        defEl.classList.add('gx-connected');
        connector.setConnection(cardId, termEl, defEl, 'pending');
        announce('Connected.');
        updateProgress();
    }

    function handleBoxClick(el) {
        if (locked) { return; }
        var side = el.getAttribute('data-side');

        if (side === 'term') {
            if (selectedTerm === el) { clearSelectionStyles(); return; }
            if (selectedTerm) { selectedTerm.classList.remove('gx-selected'); }
            selectedTerm = el;
            el.classList.add('gx-selected');
            if (selectedDef) {
                connect(selectedTerm, selectedDef);
                clearSelectionStyles();
            }
        } else {
            if (selectedDef === el) { clearSelectionStyles(); return; }
            if (selectedDef) { selectedDef.classList.remove('gx-selected'); }
            selectedDef = el;
            el.classList.add('gx-selected');
            if (selectedTerm) {
                connect(selectedTerm, selectedDef);
                clearSelectionStyles();
            }
        }
    }

    termBoxes.concat(defBoxes).forEach(function (el) {
        el.addEventListener('click', function () { handleBoxClick(el); });
        el.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleBoxClick(el); }
        });
    });

    resetBtn.addEventListener('click', function () {
        if (locked) { return; }
        connections = {};
        connector.clear();
        termBoxes.concat(defBoxes).forEach(function (el) { el.classList.remove('gx-connected', 'gx-selected'); });
        clearSelectionStyles();
        updateProgress();
        announce('Connections cleared.');
    });

    function showBanner(text, kind) {
        bannerEl.textContent = text;
        bannerEl.className = 'gx-status-banner gx-visible gx-banner-' + kind;
    }

    function lockBoard() {
        locked = true;
        termBoxes.concat(defBoxes).forEach(function (el) {
            el.classList.add('gx-locked');
            el.setAttribute('tabindex', '-1');
        });
        submitBtn.disabled = true;
        resetBtn.disabled = true;
    }

    function reveal(perItem) {
        perItem.forEach(function (result) {
            var termEl = termByCardId[result.id];
            if (!termEl) { return; }
            connector.setState(result.id, result.correct ? 'correct' : 'incorrect');
            termEl.classList.add(result.correct ? 'gx-correct' : 'gx-incorrect');

            var connectedTag = connections[result.id];
            var connectedDefEl = connectedTag ? defByTag[connectedTag] : null;
            if (connectedDefEl) {
                connectedDefEl.classList.add(result.correct ? 'gx-correct' : 'gx-incorrect');
            }
            if (!result.correct) {
                // Find the definition box whose text is the true correct answer, to draw
                // a dashed "should have gone here" line.
                var correctDefEl = defBoxes.filter(function (el) {
                    return el.querySelector('.gx-matching-box-text').textContent.trim() === result.correct_answer;
                })[0];
                if (correctDefEl) {
                    connector.addMistargetLine(result.id, correctDefEl);
                    correctDefEl.classList.add('gx-correct');
                }
            }
        });
    }

    submitBtn.addEventListener('click', function () {
        submitBtn.disabled = true;
        var pairs = {};
        Object.keys(connections).forEach(function (cardId) { pairs[cardId] = connections[cardId]; });

        $.ajax({
            type: 'POST',
            url: submitUrl,
            data: JSON.stringify({ pairs: pairs }),
            contentType: 'application/json',
            dataType: 'json',
            success: function (response) {
                lockBoard();
                reveal(response.per_item);
                var correctCount = response.per_item.filter(function (r) { return r.correct; }).length;
                var message = correctCount + ' / ' + response.per_item.length + ' correct.';
                if (response.is_new_best) { message += ' New best score!'; }
                showBanner(message, response.fraction === 1 ? 'success' : 'warning');
                announce(message);

                var attemptsEl = $('#gx-matching-attempts', element)[0];
                if (attemptsEl && response.max_attempts) {
                    attemptsEl.textContent = 'Attempts used: ' + response.attempts + ' / ' + response.max_attempts;
                }
                if (response.attempts_remaining === 0) {
                    showBanner(message + ' No attempts remaining.', 'warning');
                } else {
                    var retryLabel = response.attempts_remaining === null
                        ? 'Try again'
                        : 'Try again (' + response.attempts_remaining + ' left)';
                    $('<button type="button" class="gx-btn gx-btn-secondary"></button>')
                        .text(retryLabel)
                        .on('click', function () { window.location.reload(); })
                        .appendTo($(element).find('.gx-footer'));
                }
            },
            error: function (xhr) {
                submitBtn.disabled = false;
                var message = 'Could not submit your answer. Please try again.';
                if (xhr.status === 403) { message = 'No attempts remaining.'; }
                showBanner(message, 'warning');
            },
        });
    });

    updateProgress();
}
