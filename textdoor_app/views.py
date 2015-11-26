from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic import View, FormView
from form_views import form_templates
from models import EludeUser, BookImage, Book, Watchlist, BookRentedOut, BookYouAreRenting, BookTradingOut
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
import search_algorithm
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


saved_variable_for_search = 'Find Your Book'
redirect_page_to_search = False
shopping_cart_list = []
search_from_home = False
user_id = "guest"
guest_state = 'None'


class TextDoorHomePageView(View):

    def get(self, request):
        global user_id
        global search_from_home
        search_from_home = True
        if request.user.is_authenticated:
            user_name = request.user.username
        else:
            user_name = "guest"
        return render(request, 'home_page.html', {'user_name': user_name})


class LoggedInMixin(object):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoggedInMixin, self).dispatch(*args, **kwargs)


class SignUpPageView(View):

    def get(self, request):
        global current_search_state
        current_search_state = None
        form = form_templates.UserSignUpForm()
        return render(request, 'sign_up_page.html', {'form': form})

    def post(self, request):
        form = form_templates.UserSignUpForm(request.POST)
        if form.is_valid():
            user_name = form.cleaned_data.get('user_name')
            password = form.cleaned_data['password']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            user = User.objects.create_user(username=user_name, password=password, email=email, first_name=first_name,
                                            last_name=last_name)
            user.save()
            college_attending = form.cleaned_data['user_college']

            elude_user = EludeUser(username=user, college_attending=college_attending, new_user=True)
            elude_user.save()
            if redirect_page_to_search:
                return HttpResponseRedirect(reverse('search_result_page',
                                                    kwargs={'user_name':user_name}))
            return HttpResponseRedirect(reverse('user_home_profile_page',
                                                kwargs={'user_name': user_name}))
        else:
            return render(request, 'sign_up_page.html', {'form': form})


class UserHomeProfilePage(LoggedInMixin, View):

    def get(self, request, user_name):
        first_name = User.objects.get(username=request.user.username)
        elude_user = EludeUser.objects.get(username=request.user)
        new_user = elude_user.new_user
        if request.user.is_authenticated():
            return render(request, 'user_profile_page.html', {'user_name': user_name, 'first_name': first_name,
                                                              'first_time_user': new_user})
        else:
            return HttpResponseRedirect(reverse('login_page'))

    def post(self, request, user_name):
        logout(request)
        return HttpResponseRedirect(reverse('logout'))


class LogoutView(View):

    def get(self, request):
        return render(request, 'home_page.html')


class LoginViews(FormView):

    form_class = form_templates.LogInForm
    template_name = 'log_in_page.html'

    def get_success_url(self):
        global redirect_page_to_search
        global user_id
        self.success_url = 'user_home_profile_page'
        first_name = User.objects.get(pk=self.request.user.id)
        elude_user = EludeUser.objects.get(username=first_name)
        elude_user.new_user = False
        elude_user.save()
        if redirect_page_to_search:
            user_id = int(elude_user.id)
            return reverse('search_result_page', kwargs={'user_name': self.request.user.username})
        return reverse(self.success_url, kwargs={'user_name': self.request.user.username})

    def form_valid(self, form):
        name = form.cleaned_data['name']
        password = form.cleaned_data['password']
        user = authenticate(username=name, password=password)
        try:
            EludeUser.objects.get(username=User.objects.get(first_name=name))
            value = "used"
        except EludeUser.DoesNotExist:
            value = None
        if user is not None and value is not None:
            login(self.request, user)
            return HttpResponseRedirect(self.get_success_url())
        else:
            return render(self.request,'log_in_page.html', {'form': form})


class NewBookListingView(LoggedInMixin, View):

    def get(self, request, user_name):
        form = form_templates.RegisterBookForm()
        return render(request, 'new_book_entry.html', {'form': form, 'user_name': user_name})

    def post(self, request, user_name):
        form = form_templates.RegisterBookForm(request.POST, request.FILES)
        if form.is_valid():
            name_of_book = form.cleaned_data.get('book_name')
            isbn_num = form.cleaned_data.get('isbn')
            author = form.cleaned_data.get('author')
            image_file = request.FILES['images']
            price = form.cleaned_data.get('price')
            book_condition = form.cleaned_data.get('book_condition')
            user = User.objects.get(username=user_name)
            new_book = Book(title=name_of_book, isbn_number=isbn_num, author=author, price=price,
                            book_condition=book_condition)
            if 'for_long_term_rent' in request.GET:
                new_book.long_term_rent = True
            else:
                new_book.long_term_rent = False
            if 'for_short_term_rent' in request.GET:
                new_book.short_term_rent = True
            else:
                new_book.short_term_rent = False
            if 'for_sale' in request.GET:
                new_book.for_buy = True
            else:
                new_book.for_buy = False
            if 'for_trade' in request.GET:
                new_book.for_trade = True
            else:
                new_book.for_trade = False
            new_book.book_owner = EludeUser.objects.get(username=user)
            new_book.save()
            book_image = BookImage(image_name=(name_of_book + " book image"), book_image=image_file, book=new_book)
            book_image.save()
            return HttpResponseRedirect(reverse('success_url_page', kwargs={'user_name': user_name}))
        else:
            return render(request, 'new_book_entry.html', {'form': form})


class SuccessPageView(View):
    def get(self, request, user_name):
        return render(request, 'success_url.html', {'user_name':user_name})


class CartView(LoggedInMixin, View):
    def get(self, request, user_name):
        global shopping_cart_list
        return render(request, 'cart.html', {'cart': shopping_cart_list,'user_name': user_name})


class SearchResultView(View):

    def get(self, request, user_name):
        global redirect_page_to_search
        global saved_variable_for_search
        global search_from_home
        global guest_state
        query_string = saved_variable_for_search
        entry_query = search_algorithm.get_query(query_string, ['title', 'isbn_number', 'author'])
        found_entries = Book.objects.filter(entry_query).order_by('publish_date')
        if 'q' in request.GET and request.GET['q'].strip():
            query_string = str(request.GET['q'])
            entry_query = search_algorithm.get_query(query_string, ['title', 'isbn_number', 'author'])
            found_entries = Book.objects.filter(entry_query).order_by('publish_date')
            saved_variable_for_search = str(query_string)
        elif redirect_page_to_search:
            query_string = saved_variable_for_search
            entry_query = search_algorithm.get_query(query_string, ['title', 'isbn_number', 'author'])
            found_entries = Book.objects.filter(entry_query).order_by('publish_date')
        return render(request, 'search_results.html',
                          {'query_string': query_string, 'found_entries': found_entries,
                            'user_name':user_name, 'guest_state': guest_state, 'redirect_page': redirect_page_to_search,
                           'cart': shopping_cart_list},
                          context_instance=RequestContext(request))

    def post(self, request, user_name):
        global shopping_cart_list
        if request.POST['add_to_cart']:
            book_slug = request.POST['add_to_cart']
            book = get_object_or_404(Book, slug=book_slug)
            if len(shopping_cart_list) > 0:
                if book not in shopping_cart_list:
                    shopping_cart_list.append(book)
            else:
                shopping_cart_list.append(book)
            return HttpResponseRedirect('')


class ListOfYourBooksView(LoggedInMixin, View):

    def get(self, request, user_name):
        user = User.objects.get(username=user_name)
        elude_user = EludeUser.objects.get(username=user)
        user_book = Book.objects.filter(book_owner=elude_user)
        return render(request, 'all_user_books.html', {'user_book': user_book})


class SingleBookDescriptionView(View):

    def get(self, request, book_id, slug):
        global guest_state
        global redirect_page_to_search
        if request.user.is_authenticated():
            guest_state = "false"
            redirect_page_to_search = False
        book = get_object_or_404(Book, slug=slug)
        book_image = BookImage.objects.filter(book=book).values()
        return render(request, 'book_discription_view.html', {'book':book,'book_id':book_id,
                                                                'book_image': book_image,
                                                              'user_name': request.user.username,
                                                              'guest_state': guest_state})

    def post(self, request, book_id, slug):
        global shopping_cart_list
        global guest_state
        global redirect_page_to_search
        if 'watch-list' in request.POST:
            book = get_object_or_404(Book, slug=slug)
            if request.user.is_authenticated():
                guest_state = "false"
                redirect_page_to_search = False
                elude_user = EludeUser.objects.get(username=request.user)
                try:
                    Watchlist.objects.get(book=book, user=elude_user)
                    no_entry = "This Works"
                except Watchlist.DoesNotExist:
                    no_entry = None
                if no_entry is None:
                    new_watch_list = Watchlist(book=book, user=elude_user)
                    new_watch_list.save()
            else:
                guest_state = "true"
                redirect_page_to_search = True
            return HttpResponseRedirect('')

        if 'add_to_cart' in request.POST:
            book = get_object_or_404(Book, slug=slug)
            if len(shopping_cart_list) > 0:
                if book not in shopping_cart_list:
                    shopping_cart_list.append(book)
            else:
                shopping_cart_list.append(book)
            if request.user.is_authenticated():
                guest_state = "false"
                redirect_page_to_search = False
            else:
                guest_state = "true"
                redirect_page_to_search = True
            return HttpResponseRedirect('')


class WatchListBooksView(LoggedInMixin, View):

    def get(self, request, user_name):
        user = User.objects.get(username=request.user.username)
        elude_user = EludeUser.objects.get(username=user)
        try:
            books = Watchlist.objects.filter(user=elude_user)
        except Watchlist.DoesNotExist:
            books = None
        return render(request, 'watch_list_books.html', {'books': books, 'elude_user': elude_user})
'''
class OrderHistoryView(View):

    def get(self, request, pk, user_name):
        user = User.objects.get(username=user_name)

'''


class BooksOutOnRentView(LoggedInMixin, View):

    def get(self, request, user_name):
        user = User.objects.get(username=user_name)
        elude_user = EludeUser.objects.get(username=user)
        try:
            books = BookRentedOut.objects.filter(user=elude_user)
        except BookRentedOut.DoesNotExist:
            books = None
        return render(request, 'books_out_on_rent.html', {'books':books, 'elude_user': elude_user})


class BooksYouAreRentingView(LoggedInMixin, View):

    def get(self, request, user_name):
        try:
            user = User.objects.get(username=request.user.username)
            elude_user = EludeUser.objects.get(username=user)
        except User.DoesNotExist:
            elude_user = None
        try:
            books = BookYouAreRenting.objects.filter(user=elude_user)
        except BookYouAreRenting.DoesNotExist:
            books = None
        return render(request, 'book_you_are_renting.html', {'books': books, 'elude_user': elude_user})


class TradeHistoryView(View):

    def get(self, request, user_name):
        user = User.objects.get(username=user_name)
        elude_user = EludeUser.objects.get(username=user)
        try:
            books = BookTradingOut.objects.filter(user=elude_user)
        except BookTradingOut.DoesNotExist:
            books = None
        return render(request, 'books_out_on_rent.html', {'books': books, 'elude_user': elude_user})


