/* Sequencing game: drag (or use Move up/down) to reorder shuffled steps into
 * the correct order, then submit for scoring. */
function GamesXBlockSequencing(runtime, element) {
    'use strict';

    var listEl = $('#gx-sequencing-list', element)[0];
    if (!listEl) { return; } // no items configured

    var submitBtn = $('#gx-sequencing-submit', element)[0];
    var bannerEl = $('#gx-sequencing-banner', element)[0];
    var announceEl = $('#gx-sequencing-announce', element)[0];
    var submitUrl = runtime.handlerUrl(element, 'submit_sequencing');
    var locked = false;
    var currentOrder = Array.prototype.map.call(listEl.querySelectorAll('.gx-sequencing-item'), function (el) {
        return el.getAttribute('data-id');
    });

    function announce(message) {
        if (!announceEl) { return; }
        announceEl.textContent = '';
        void announceEl.offsetHeight;
        announceEl.textContent = message;
    }

    window.GamesXBlockDnD.makeSortable(listEl, '.gx-sequencing-item', function (orderedIds) {
        currentOrder = orderedIds;
        announce('Order updated.');
    });

    function showBanner(text, kind) {
        bannerEl.textContent = text;
        bannerEl.className = 'gx-status-banner gx-visible gx-banner-' + kind;
    }

    function lockList() {
        locked = true;
        Array.prototype.forEach.call(listEl.querySelectorAll('.gx-sequencing-item'), function (el) {
            el.setAttribute('draggable', 'false');
            el.querySelectorAll('button').forEach(function (btn) { btn.disabled = true; });
        });
        submitBtn.disabled = true;
    }

    function reveal(perItem) {
        var itemsById = {};
        Array.prototype.forEach.call(listEl.querySelectorAll('.gx-sequencing-item'), function (el) {
            itemsById[el.getAttribute('data-id')] = el;
        });
        perItem.forEach(function (result) {
            var el = itemsById[result.id];
            if (!el) { return; }
            el.classList.add(result.correct ? 'gx-correct' : 'gx-incorrect');
            if (!result.correct && typeof result.correct_position === 'number') {
                var note = document.createElement('div');
                note.className = 'gx-reveal-answer';
                note.textContent = 'Correct position: ' + (result.correct_position + 1);
                el.appendChild(note);
            }
        });
    }

    submitBtn.addEventListener('click', function () {
        if (locked) { return; }
        submitBtn.disabled = true;

        $.ajax({
            type: 'POST',
            url: submitUrl,
            data: JSON.stringify({ order: currentOrder }),
            contentType: 'application/json',
            dataType: 'json',
            success: function (response) {
                lockList();
                reveal(response.per_item);
                var correctCount = response.per_item.filter(function (r) { return r.correct; }).length;
                var message = correctCount + ' / ' + response.per_item.length + ' in the correct position.';
                if (response.is_new_best) { message += ' New best score!'; }
                showBanner(message, response.fraction === 1 ? 'success' : 'warning');
                announce(message);

                var attemptsEl = $('#gx-sequencing-attempts', element)[0];
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
}
