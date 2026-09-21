/* Memory / concentration: flip two cards at a time; a match is determined by
 * looking up the flipped card's tag in a server-provided tag-pair map, so
 * card identities never sit unflipped in a readable form. Ungraded -- tracks
 * completion + best time only. */
function GamesXBlockMemory(runtime, element) {
    'use strict';

    var gridEl = $('#gx-memory-grid', element)[0];
    if (!gridEl) { return; } // no pairs configured

    var bannerEl = $('#gx-memory-banner', element)[0];
    var announceEl = $('#gx-memory-announce', element)[0];
    var timerEl = $('#gx-memory-timer', element)[0];
    var completeUrl = runtime.handlerUrl(element, 'complete_memory');

    var lookupEl = $('#gx-memory-pair-lookup', element)[0];
    var tagPairLookup = {};
    try {
        tagPairLookup = JSON.parse(lookupEl.textContent);
    } catch (e) {
        tagPairLookup = {};
    }

    var cardEls = Array.prototype.slice.call(gridEl.querySelectorAll('.gx-memory-card'));
    var totalPairs = cardEls.length / 2;
    var matchedPairs = 0;
    var flipped = [];
    var busy = false;
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

    function flipCard(cardEl) {
        cardEl.classList.add('gx-flipped');
        cardEl.setAttribute('aria-label', cardEl.querySelector('.gx-memory-card-front').textContent);
    }

    function unflipCard(cardEl) {
        cardEl.classList.remove('gx-flipped');
        cardEl.setAttribute('aria-label', 'Card, face down');
    }

    function handleCardClick(cardEl) {
        if (busy || cardEl.classList.contains('gx-flipped') || cardEl.classList.contains('gx-matched')) { return; }

        flipCard(cardEl);
        flipped.push(cardEl);

        if (flipped.length < 2) { return; }

        busy = true;
        var first = flipped[0];
        var second = flipped[1];
        var isMatch = tagPairLookup[first.getAttribute('data-tag')] === second.getAttribute('data-tag');

        setTimeout(function () {
            if (isMatch) {
                first.classList.add('gx-matched');
                second.classList.add('gx-matched');
                first.disabled = true;
                second.disabled = true;
                matchedPairs += 1;
                announce('Match found!');
                if (matchedPairs === totalPairs) {
                    finish();
                }
            } else {
                unflipCard(first);
                unflipCard(second);
                announce('No match, try again.');
            }
            flipped = [];
            busy = false;
        }, isMatch ? 500 : 900);
    }

    cardEls.forEach(function (cardEl) {
        cardEl.addEventListener('click', function () { handleCardClick(cardEl); });
    });

    function finish() {
        if (timerInterval) { clearInterval(timerInterval); }
        var elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        bannerEl.textContent = 'You matched every pair!';
        bannerEl.className = 'gx-status-banner gx-visible gx-banner-success';
        announce('Congratulations, you matched every pair!');

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
