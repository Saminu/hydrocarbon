// base.js
// 141211
// - initial version

$(function() {

	$window = $(window);
	$document = $(document);
	$overlay = $('#overlay');
	$tooltip = $('#tooltip');

	$('.hoverable').hover(function() { $(this).addClass('hover'); },
			function() { $(this).removeClass('hover'); });

	$document
		.on('mouseenter', '.th', showTooltip)
		.on('mouseleave scroll', '.th', hideTooltip)
		.on('mouseenter', '*[title]', function() {
			$(this)
				.data('title', $(this).attr('title'))
				.removeAttr('title')
				.addClass('th')
				.trigger('mouseenter');
		});		

	$('#form_login')
		.on('load focusin focusout', '.field input', function() {
			if(this.value == '') { $(this).next('label').show();
			} else { $(this).next('label').hide(); }
		})
		.on('keypress', '.field input', function() {
			$(this).next('label').hide();
		});

	$('.vote a').on('click', function(e) {
		e.preventDefault();

		var $sibling_voted = $(this).siblings('.voted');

		var vote;
		var avote;
		var work;
		var button;
		var callback;

		var databox = {
			type: null,
			target: null,
			vote: null
		}

		if($(this).hasClass('vote-post')) databox.type = 'p';
		if($(this).hasClass('vote-comment')) databox.type = 'c';

		databox.target = $(this).parent('.vote').data('target-id');

		if($(this).hasClass('voted')) { work = '-';
		} else { work = '+'; }

		if($(this).hasClass('upvote')) { 
			vote = '+';
			avote = '-';
		}
		if($(this).hasClass('downvote')) {
			vote = '-';
			avote = '+';
		}

		button = $(this);

		if(work == '+' && $sibling_voted.length) {
			$ajax_vote(databox, '-' + avote, $sibling_voted)
				.done(function() { $ajax_vote(databox, work + vote, button); });
		} else { $ajax_vote(databox, work + vote, button); }
	});

});

var $overlay;
var $tooltip;

var csrftoken = $.cookie('csrftoken');

var funct = function() {};

var browser = {
	can : {
		placeholder: function() { return 'placeholder' in document.creatElement('input'); }
	}
}

function csrfSafeMethod(method) { return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method)); }

$.ajaxSetup({
	beforeSend: function(xhr, settings) {
		if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		}
	}
});

function showTooltip(e) {
	var $target = $(e.target).closest('.th');
	var position = $target.offset();

	var targetHeight = $target.outerHeight();
	var targetWidth = $target.outerWidth();

	var offsetY;
	var offsetX;

	var top;
	var left;

	var height;
	var width;

	$tooltip.find('.container p').text($target.data('title'));
	$tooltip.find('.tip').removeAttr('style');

	top = position.top + targetHeight;
	left = position.left + targetWidth/2;

	height = $tooltip.height();
	width = $tooltip.width();

	offsetX = $window.width() - (left + width/2);
	offsetY = $window.height() - (top + height);

	offsetX = (offsetX < 0) ? offsetX - 10 : 0;
	offsetY = (offsetY < 0) ? -1*(height + targetHeight) - 2 : 2;

	$tooltip
		.css({
			'top': top + offsetY,
			'left': left - width/2 + offsetX
		})
		.show()
		.stop()
		.animate({'opacity': 1}, 100)
		.find('.tip')
			.hide()
			.css('margin-left', -2*offsetX)
			.filter((offsetY > 0) ? '.top' : '.bottom').show();
}

function hideTooltip() {
	$tooltip
		.stop()
		.animate({'opacity': 0}, 100, function() { $tooltip.hide(); });
}

function $ajax_vote(databox, vote, button) {
	databox.vote = vote;
	return $.ajax({
			type: 'POST',
			url: '/x/v',
			data: databox
		})
			.done(function(data, status, xhr) {
				if(databox.vote.charAt(0) == '+') { button.addClass('voted');
				} else { button.removeClass('voted'); }
			})
			.fail(function(xhr, status, error) {
				console.log(status);
				console.log(error);
			});
}