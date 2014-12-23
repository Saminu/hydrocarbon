function getComments(id) {
	return $.ajax({
		type: 'GET',
		url: '/x/c/' + id
	})
		.done(function(data, status, xhr) {
			var $article = $('.section.article'), $container = $('.comments-list ul'), count = data.comments.length;
			$container.find('.list.item, .clone').remove();

			$.each(data.comments, function(i, v) { renderComment($container, v); });

			$article
				.find('.item.article .header .label.meta.comments .text, .item.article .footer .label.meta.comments .text span')
				.add('.post-id-'+id+' .label.meta.comments .text')
					.text(count);

			$('.comments-list .write textarea').val('');
		})
		.fail(function(xhr, status, error) {
			console.log(xhr);
			console.log(status);	
			console.log(error);

			alert('댓글을 불러오는 과정에서 오류가 발생했습니다.');
		});
}

function renderComment($container, v) {
	var $c = $container.find('.list.template').clone(), date = new Date(v.created_time);

	if(v.iphash) {
		$c.find('.meta.author')
			.removeClass('user')
			.addClass('guest')
			.attr('title', v.iphash);
	}

	$c.find('.meta.author .text').text(v.author);
	$c.find('.meta.timestamp')
		.attr('title', date.toLocaleString('ko-kr', { hour12: false }))
		.text($.timeago(v.created_time));
	$c.find('.article').html(v.contents);

	$c
		.data('id', v.id)
		.addClass('item')
		.removeClass('template')
		.insertBefore($container.find('.write.template'))
		.show();

	if(v.subcomments) {
		$.each(v.subcomments, function(i, v) {
			renderComment($container, v)
				.css('margin-left', '2%');
		});
	}

	return $c;
}

function postComments(id, databox) {
	return $.ajax({
		type: 'POST',
		url: '/x/c/' + id,
		data: databox
	})
		.fail(function(xhr, status, error) {
			console.log(xhr);
			console.log(status);
			console.log(error);

			alert('댓글을 등록하는 과정에서 오류가 발생했습니다.');
		});
}

function putComments(id, contents, password) {
	return $.ajax({
		type: 'PUT',
		url: '/x/c/' + id,
		data: { contents: contents },
		headers: { 'X-HC-PASSWORD': password }
	})
		.fail(function(xhr, status, error) {
			console.log(xhr);
			console.log(status);
			console.log(error);

			alert('댓글을 수정하는 과정에서 오류가 발생했습니다.');
		});
}

function deleteComments(id, password) {
	return $.ajax({
		type: 'DELETE',
		url: '/x/c/' + id,
		headers: { 'X-HC-PASSWORD': password }
	})
		.fail(function(xhr, status, error) {
			console.log(xhr);
			console.log(status);
			console.log(error);

			alert('댓글을 삭제하는 과정에서 오류가 발생했습니다.');
		});
}

$(function() {
	$('.comments-list')
		.on('click', '.write .submit', function(e) {
			e.preventDefault();
			var $container = $(this).closest('.write'),
				text = $container.find('textarea').val(),
				nick = $container.find('.footer label.nick input').val(),
				password = $container.find('.footer label.password input').val(),
				id = $('.section.article').data('id'),
				databox = {
					contents: text,
					type: $container.data('type'),
					ot_nick: nick,
					ot_password: password
				};

			if(text == '') {
				alert('내용을 입력해 주세요.');
				return false;
			}

			if($container.data('type') == 'c') id = $container.prev('li.item').data('id');
			console.log(databox);
			postComments(id, databox)
				.done(getComments(id));
		})
		.on('click', '.modify .submit', function(e) {
			e.preventDefault();
			var $container = $(this).closest('.modify'),
				text = $container.find('textarea').val(),
				id = $container.data('id'),
				password = $container.find('.footer label.password input').val();

			console.log(password);

			if(text == '') {
				alert('내용을 입력해 주세요.');
				return false;
			}

			if(password == '') {
				alert('비밀번호를 입력해 주세요.');
				return false;
			}

			putComments(id, text, password)
				.done(getComments($('.section.article').data('id')));
		})
		.on('click', '.delete .submit', function(e) {
			e.preventDefault();
			var $item = $(this).closest('li.item'),
				password = $item.find('.footer label.password input').val();

			deleteComments($item.data('id'), password)
				.done(getComments($('.section.article').data('id')));
		})
		.on('click', '.dropdown.menu li a', function(e) {
			e.preventDefault();

			var $container = $('.comments-list ul'), action = $(this).attr('href').replace('#', '');

			switch(action) {
				case 'upvote':
					break;

				case 'downvote':
					break;

				case 'reply':
					var $c = $container.find('.write.template').clone();
					$c
						.css('margin-left', '2%')
						.removeAttr('data-type')
						.data('type', 'c')
						.addClass('clone')
						.removeClass('template')
						.insertAfter($(this).closest('li.item'))
						.show();
					break;

				case 'modify':
					var $c = $container.find('.write.template').clone(), $item = $(this).closest('li.item');
					$item.hide();
					$c
						.removeAttr('data-type')
						.data('id', $item.data('id'))
						.addClass('clone modify')
						.removeClass('template write')
						.insertAfter($item)
						.show();

					$c.find('label.nick')
						.remove();

					$c.find('textarea')
						.val($item.find('.article').text());

					$c.find('.cancel')
						.show();

					break;

				case 'delete':
					var $c = $container.find('.write.template .footer').clone(), $item = $(this).closest('li.item .bubble.item > .container');

					$item.addClass('delete');

					$c.appendTo($item);

					$c.find('label.nick')
						.remove();

					$c.find('.cancel')
						.show();

					$c.find('.submit')
						.text('삭제');
					break;

				default:
					console.log(action);
			}
		})
		.on('click', '.cancel', function(e) {
			e.preventDefault();
			var $c = $(this).closest('.write.modify');

			$c.prev('li.item').show();
			$c.hide();
		});
});
