function getComments(id) {
	return $.ajax({
		type: 'GET',
		url: '/x/c/' + id
	})
		.done(function(data, status, xhr) {
			var $article = $('.section.article'), $container = $('.comments-list ul'), count = data.comments.count;
			$container.find('.list.item, .clone').remove();

			$.each(data.comments.list, function(i, v) { renderComment($container, v); });

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

function renderComment($container, v, depth) {
	depth = typeof depth !== 'undefined' ? depth : 0;

	var $c = $container.find('.list.template').clone(), date = new Date(v.created_time);

	console.log(v);

	if(v.iphash) {
		$c
			.addClass('guest')
			.find('.meta.author')
				.removeClass('user')
				.addClass('guest')
				.attr('title', v.iphash);
	} else if(v.author == author) {
		$c.addClass('owned');
	}
	if(c3RhZmY) {
		$c.find('.manipulate').show();
	}

	if(depth > 0) $c.css('margin-left', 2*depth+'%');

	$c.find('.meta.author .text').text(v.author);
	$c.find('.meta.timestamp')
		.attr('title', date.toLocaleString('ko-kr', { hour12: false }))
		.text($.timeago(v.created_time));
	$c.find('.meta.score')
		.attr('title', '+'+v.votes.upvote+' / -'+v.votes.downvote)
		.find('.text span').text(v.votes.total);

	contents = v.contents;
	contents = contents.replace(/\n/g, '<br>', 'g');
	$c.find('.article').html(contents);

	if(v.voted.upvoted) $c.find('.dropdown .upvote').addClass('voted');
	if(v.voted.downvoted) $c.find('.dropdown .downvote').addClass('voted');

	$c
		.data('id', v.id)
		.data('depth', depth)
		.addClass('item')
		.removeClass('template')
		.insertBefore($container.find('.write.template'))
		.show();

	if(v.subcomments) {
		$.each(v.subcomments, function(i, v) { renderComment($container, v, depth + 1); });
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
	$('.section.article .item.article .footer')
		.on('click', 'a', function(e) {
			var action = $(this).attr('href').replace('#', '');

			switch(action) {
				case 'toggle':
					e.preventDefault();
					$('#comments').toggle();
					break;

				case 'refresh':
					e.preventDefault();
					getComments($('.section.article').data('id'));
					break;
			}
		});


	$('.comments-list')
		.on('click', '.write .submit', function(e) {
			e.preventDefault();
			var $container = $(this).closest('.write'),
				text = $container.find('textarea').val(),
				nick = $container.find('.footer label.nick input').val(),
				password = $container.find('.footer label.password input').val(),
				id = $container.data('id'),
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
				.done(function() { getComments(post_id) });
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
				.done(function() { getComments(post_id) });
		})
		.on('click', '.delete .submit', function(e) {
			e.preventDefault();
			var $item = $(this).closest('li.item'),
				password = $item.find('.footer label.password input').val();

			deleteComments($item.data('id'), password)
				.done(function() { getComments(post_id) });
		})
		.on('click', '.dropdown.menu li a', function(e) {
			e.preventDefault();

			var $container = $('.comments-list ul'), action = $(this).attr('href').replace('#', '');

			switch(action) {
				case 'upvote':
				case 'downvote':
					var button  = $(this).closest('li.vote'),
						$item = $(this).closest('li.item');
					vote('c', $item.data('id'), button);

					break;

				case 'reply':
					var $c = $container.find('.write.template').clone(), $item = $(this).closest('li.item');
					$c
						.css('margin-left', $item.data('depth')*2 + 1 + '%')
						.removeAttr('data-type data-id')
						.data('type', 'c')
						.data('id', $item.data('id'))
						.addClass('clone')
						.removeClass('template')
						.insertAfter($item)
						.show();
					break;

				case 'modify':
					var $c = $container.find('.write.template').clone(), $item = $(this).closest('li.item');
					$item.hide();
					$c
						.css('margin-left', $item.css('margin-left'))
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
