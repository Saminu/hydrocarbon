from haystack import indexes

from board.models import Comment, Post, Tag


class PostIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    board = indexes.CharField(model_attr='board__slug')
    author = indexes.CharField(model_attr='author')

    def get_model(self):
        return Post


class CommentIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='contents', document=True)
    post = indexes.IntegerField(model_attr='post__id', indexed=False)
    board = indexes.CharField(model_attr='post__board__slug')
    author = indexes.CharField(model_attr='author')

    def get_model(self):
        return Comment


class TagIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='normalized', document=True)

    def get_model(self):
        return Tag
