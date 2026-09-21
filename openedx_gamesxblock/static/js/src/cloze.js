/* Cloze game: drag words from the bank into blanks in a passage, then submit
 * for scoring. Each blank holds exactly one word; clicking a filled blank
 * (with no word armed) returns its word to the bank. */
function GamesXBlockCloze(runtime, element) {
    'use strict';

    var passageEl = $('#gx-cloze-passage', element)[0];
    var bankEl = $('#gx-cloze-bank', element)[0];
    if (!passageEl || !bankEl) { return; } // no blanks configured

    var submitBtn = $('#gx-cloze-submit', element)[0];
    var bannerEl = $('#gx-cloze-banner', element)[0];
    var announceEl = $('#gx-cloze-announce', element)[0];
    var submitUrl = runtime.handlerUrl(element, 'submit_cloze');
    var locked = false;

    var blanks = Array.prototype.slice.call(passageEl.querySelectorAll('.gx-cloze-blank'));
    var totalBlanks = blanks.length;
    // fill: targetId (blank token) -> { wordId, word }
    var fill = {};

    function announce(message) {
        if (!announceEl) { return; }
        announceEl.textContent = '';
        void announceEl.offsetHeight;
        announceEl.textContent = message;
    }

    function updateSubmitState() {
        submitBtn.disabled = locked || Object.keys(fill).length !== totalBlanks;
    }

    function wordElById(wordId) {
        return bankEl.querySelector('[data-id="' + wordId + '"]') ||
            passageEl.querySelector('[data-id="' + wordId + '"]');
    }

    function placeWordInBlank(wordId, targetId) {
        var wordEl = wordElById(wordId);
        var blankEl = passageEl.querySelector('[data-target-id="' + targetId + '"]');
        if (!wordEl || !blankEl) { return; }

        // If this blank already holds a word, return it to the bank first.
        if (fill[targetId]) {
            returnWordToBank(fill[targetId].wordId);
        }
        // If this word was already placed elsewhere, clear that blank first.
        Object.keys(fill).forEach(function (existingTargetId) {
            if (fill[existingTargetId].wordId === wordId && existingTargetId !== targetId) {
                delete fill[existingTargetId];
                var oldBlank = passageEl.querySelector('[data-target-id="' + existingTargetId + '"]');
                if (oldBlank) {
                    oldBlank.classList.remove('gx-filled');
                    oldBlank.removeAttribute('data-filled-id');
                    oldBlank.textContent = ' ';
                }
            }
        });

        var word = wordEl.getAttribute('data-word');
        fill[targetId] = { wordId: wordId, word: word };
        blankEl.textContent = word;
        blankEl.classList.add('gx-filled');
        blankEl.setAttribute('data-filled-id', wordId);
        wordEl.style.display = 'none';
        announce(word + ' placed.');
        updateSubmitState();
    }

    function returnWordToBank(wordId) {
        var targetId = Object.keys(fill).filter(function (t) { return fill[t].wordId === wordId; })[0];
        if (targetId === undefined) { return; }
        delete fill[targetId];
        var blankEl = passageEl.querySelector('[data-target-id="' + targetId + '"]');
        if (blankEl) {
            blankEl.classList.remove('gx-filled');
            blankEl.removeAttribute('data-filled-id');
            blankEl.textContent = ' ';
        }
        var wordEl = wordElById(wordId);
        if (wordEl) { wordEl.style.display = ''; }
        announce('Word returned to bank.');
        updateSubmitState();
    }

    window.GamesXBlockDnD.makeDroppable(bankEl, '.gx-cloze-word', passageEl, '.gx-cloze-blank', placeWordInBlank, returnWordToBank);

    function showBanner(text, kind) {
        bannerEl.textContent = text;
        bannerEl.className = 'gx-status-banner gx-visible gx-banner-' + kind;
    }

    function lockGame() {
        locked = true;
        submitBtn.disabled = true;
        Array.prototype.forEach.call(bankEl.querySelectorAll('.gx-cloze-word'), function (el) {
            el.setAttribute('draggable', 'false');
            el.setAttribute('tabindex', '-1');
        });
        blanks.forEach(function (el) { el.setAttribute('tabindex', '-1'); });
    }

    function reveal(perItem) {
        perItem.forEach(function (result) {
            var blankEl = passageEl.querySelector('[data-target-id="' + result.id + '"]');
            if (!blankEl) { return; }
            blankEl.classList.add(result.correct ? 'gx-correct' : 'gx-incorrect');
            if (!result.correct) {
                var note = document.createElement('div');
                note.className = 'gx-reveal-answer';
                note.textContent = 'Correct answer: ' + result.correct_answer;
                blankEl.parentNode.insertBefore(note, blankEl.nextSibling);
            }
        });
    }

    submitBtn.addEventListener('click', function () {
        if (locked) { return; }
        submitBtn.disabled = true;

        var fillPayload = {};
        Object.keys(fill).forEach(function (targetId) { fillPayload[targetId] = fill[targetId].word; });

        $.ajax({
            type: 'POST',
            url: submitUrl,
            data: JSON.stringify({ fill: fillPayload }),
            contentType: 'application/json',
            dataType: 'json',
            success: function (response) {
                lockGame();
                reveal(response.per_item);
                var correctCount = response.per_item.filter(function (r) { return r.correct; }).length;
                var message = correctCount + ' / ' + response.per_item.length + ' blanks correct.';
                if (response.is_new_best) { message += ' New best score!'; }
                showBanner(message, response.fraction === 1 ? 'success' : 'warning');
                announce(message);

                var attemptsEl = $('#gx-cloze-attempts', element)[0];
                if (attemptsEl && response.max_attempts) {
                    attemptsEl.textContent = 'Attempts used: ' + response.attempts + ' / ' + response.max_attempts;
                }
                if (response.attempts_remaining !== 0) {
                    var retryLabel = response.attempts_remaining === null
                        ? 'Try again'
                        : 'Try again (' + response.attempts_remaining + ' left)';
                    $('<button type="button" class="gx-btn gx-btn-secondary"></button>')
                        .text(retryLabel)
                        .on('click', function () { window.location.reload(); })
                        .appendTo($(element).find('.gx-footer'));
                } else {
                    showBanner(message + ' No attempts remaining.', 'warning');
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

    updateSubmitState();
}
