/**
 * ArrowConnector: draws and maintains SVG connector lines between pairs of
 * DOM elements inside a positioned container. Used by the matching game to
 * show a persistent line between a connected term and definition, redrawn
 * automatically as the layout changes.
 *
 * Usage:
 *   const connector = new ArrowConnector(containerEl);
 *   connector.setConnection('term-1', fromEl, toEl, 'pending');
 *   connector.setState('term-1', 'correct'); // or 'incorrect'
 *   connector.addMistargetLine('term-1', correctToEl); // dashed line to right answer
 *   connector.remove('term-1');
 *   connector.clear();
 *   connector.destroy();
 */
(function (global) {
    'use strict';

    var STATE_CLASS = {
        pending: 'gx-arrow-pending',
        correct: 'gx-arrow-correct',
        incorrect: 'gx-arrow-incorrect',
    };

    function ArrowConnector(container) {
        this.container = container;
        this.connections = {}; // id -> { fromEl, toEl, state, pathEl, mistargetPathEl }
        this._buildSvg();
        this._bindResize();
    }

    ArrowConnector.prototype._buildSvg = function () {
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'gx-arrow-overlay');
        svg.setAttribute('aria-hidden', 'true');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        svg.style.overflow = 'visible';
        this.svg = svg;
        this.container.appendChild(svg);
    };

    ArrowConnector.prototype._bindResize = function () {
        var self = this;
        if (typeof ResizeObserver !== 'undefined') {
            this._resizeObserver = new ResizeObserver(function () {
                self.redrawAll();
            });
            this._resizeObserver.observe(this.container);
        }
        this._scrollHandler = function () { self.redrawAll(); };
        window.addEventListener('resize', this._scrollHandler);
        window.addEventListener('scroll', this._scrollHandler, true);
    };

    /** Compute the anchor point (center of the element's edge facing the container's opposite side). */
    ArrowConnector.prototype._anchorFor = function (el, side) {
        var containerRect = this.container.getBoundingClientRect();
        var rect = el.getBoundingClientRect();
        var x = side === 'right' ? rect.right - containerRect.left : rect.left - containerRect.left;
        var y = rect.top + rect.height / 2 - containerRect.top;
        return { x: x, y: y };
    };

    ArrowConnector.prototype._pathData = function (fromEl, toEl) {
        var from = this._anchorFor(fromEl, 'right');
        var to = this._anchorFor(toEl, 'left');
        var dx = Math.max(40, Math.abs(to.x - from.x) * 0.5);
        return 'M ' + from.x + ' ' + from.y +
            ' C ' + (from.x + dx) + ' ' + from.y + ', ' +
            (to.x - dx) + ' ' + to.y + ', ' +
            to.x + ' ' + to.y;
    };

    ArrowConnector.prototype._makePath = function (dashed) {
        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('class', 'gx-arrow-line' + (dashed ? ' gx-arrow-dashed' : ''));
        path.setAttribute('fill', 'none');
        this.svg.appendChild(path);
        return path;
    };

    /** Create or update the primary connection line for `id` between fromEl and toEl. */
    ArrowConnector.prototype.setConnection = function (id, fromEl, toEl, state) {
        var entry = this.connections[id];
        if (!entry) {
            entry = { pathEl: this._makePath(false) };
            this.connections[id] = entry;
        }
        entry.fromEl = fromEl;
        entry.toEl = toEl;
        this.setState(id, state || 'pending');
        this._redrawOne(id);
    };

    /** Update only the visual state (pending/correct/incorrect) of an existing connection. */
    ArrowConnector.prototype.setState = function (id, state) {
        var entry = this.connections[id];
        if (!entry) { return; }
        entry.state = state;
        entry.pathEl.classList.remove(STATE_CLASS.pending, STATE_CLASS.correct, STATE_CLASS.incorrect);
        entry.pathEl.classList.add(STATE_CLASS[state] || STATE_CLASS.pending);
    };

    /** Draw a secondary dashed line from the term to its actual correct definition, for wrong answers. */
    ArrowConnector.prototype.addMistargetLine = function (id, correctToEl) {
        var entry = this.connections[id];
        if (!entry) { return; }
        if (!entry.mistargetPathEl) {
            entry.mistargetPathEl = this._makePath(true);
        }
        entry.mistargetToEl = correctToEl;
        this._redrawOne(id);
    };

    /** Remove one connection's line(s) entirely. */
    ArrowConnector.prototype.remove = function (id) {
        var entry = this.connections[id];
        if (!entry) { return; }
        if (entry.pathEl && entry.pathEl.parentNode) { entry.pathEl.parentNode.removeChild(entry.pathEl); }
        if (entry.mistargetPathEl && entry.mistargetPathEl.parentNode) {
            entry.mistargetPathEl.parentNode.removeChild(entry.mistargetPathEl);
        }
        delete this.connections[id];
    };

    /** Remove every connection. */
    ArrowConnector.prototype.clear = function () {
        Object.keys(this.connections).forEach(this.remove.bind(this));
    };

    ArrowConnector.prototype._redrawOne = function (id) {
        var entry = this.connections[id];
        if (!entry || !entry.fromEl || !entry.toEl) { return; }
        entry.pathEl.setAttribute('d', this._pathData(entry.fromEl, entry.toEl));
        if (entry.mistargetPathEl && entry.mistargetToEl) {
            entry.mistargetPathEl.setAttribute('d', this._pathData(entry.fromEl, entry.mistargetToEl));
        }
    };

    /** Recompute every connection's path -- call on resize/scroll/layout changes. */
    ArrowConnector.prototype.redrawAll = function () {
        var self = this;
        Object.keys(this.connections).forEach(function (id) { self._redrawOne(id); });
    };

    /** Tear down observers/listeners and remove the SVG overlay. */
    ArrowConnector.prototype.destroy = function () {
        this.clear();
        if (this._resizeObserver) { this._resizeObserver.disconnect(); }
        if (this._scrollHandler) {
            window.removeEventListener('resize', this._scrollHandler);
            window.removeEventListener('scroll', this._scrollHandler, true);
        }
        if (this.svg && this.svg.parentNode) { this.svg.parentNode.removeChild(this.svg); }
    };

    global.GamesXBlockArrowConnector = ArrowConnector;
}(window));
