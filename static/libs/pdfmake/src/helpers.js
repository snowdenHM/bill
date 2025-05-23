'use strict';

function isString(variable) {
	return typeof variable === 'string' || variable instanceof String;
}

function isNumber(variable) {
	return typeof variable === 'number' || variable instanceof Number;
}

function isBoolean(variable) {
	return typeof variable === 'boolean';
}

function isArray(variable) {
	return Array.isArray(variable);
}

function isFunction(variable) {
	return typeof variable === 'function';
}

function isObject(variable) {
	return variable !== null && typeof variable === 'object';
}

function isNull(variable) {
	return variable === null;
}

function isUndefined(variable) {
	return variable === undefined;
}

/**
 * @param {any} variable
 * @returns {boolean}
 */
function isPositiveInteger(variable) {
	if (!isNumber(variable) || !Number.isInteger(variable) || variable <= 0) {
		return false;
	}
	return true;
}

function pack() {
	var result = {};

	for (var i = 0, l = arguments.length; i < l; i++) {
		var obj = arguments[i];

		if (obj) {
			for (var key in obj) {
				if (obj.hasOwnProperty(key)) {
					result[key] = obj[key];
				}
			}
		}
	}

	return result;
}

function offsetVector(vector, x, y) {
	switch (vector.type) {
		case 'ellipse':
		case 'rect':
			vector.x += x;
			vector.y += y;
			break;
		case 'line':
			vector.x1 += x;
			vector.x2 += x;
			vector.y1 += y;
			vector.y2 += y;
			break;
		case 'polyline':
			for (var i = 0, l = vector.points.length; i < l; i++) {
				vector.points[i].x += x;
				vector.points[i].y += y;
			}
			break;
	}
}

function fontStringify(key, val) {
	if (key === 'font') {
		return 'font';
	}
	return val;
}

function getNodeId(node) {
	if (node.id) {
		return node.id;
	}

	if (isArray(node.text)) {
		for (var i = 0, l = node.text.length; i < l; i++) {
			var n = node.text[i];
			var nodeId = getNodeId(n);
			if (nodeId) {
				return nodeId;
			}
		}
	}

	return null;
}

function isPattern(color) {
	return isArray(color) && color.length === 2;
}

// converts from a [<pattern name>, <color>] as used by pdfmake
// into [<pattern object>, <color>] as used by pdfkit
// (the pattern has to be registered in the doc definition of course)
function getPattern(color, patterns) {
	return [patterns[color[0]], color[1]];
}

module.exports = {
	isString: isString,
	isNumber: isNumber,
	isBoolean: isBoolean,
	isArray: isArray,
	isFunction: isFunction,
	isObject: isObject,
	isNull: isNull,
	isUndefined: isUndefined,
	isPositiveInteger: isPositiveInteger,
	pack: pack,
	fontStringify: fontStringify,
	offsetVector: offsetVector,
	getNodeId: getNodeId,
	isPattern: isPattern,
	getPattern: getPattern
};
