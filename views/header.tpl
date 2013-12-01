% include bootstrap.tpl
<div class="navbar navbar-default navbar-fixed-top">
    <div class="container">
        <a class="navbar-brand" href="/main">BGMM</a>
        <div class="navbar-collapse">
            <ul class="nav navbar-nav">
                <li><a href="/main">Home</a></li>
                <li><a href="/config">Config</a></li>
                <li><a href="/logs">Logs</a></li>
                <li><a href="/status">Status</a></li>
            </ul>
            <ul class="nav navbar-nav pull-right">
                % if session_status["logged_in"]:
                    <li class="dropdown">
                        <a href="#" class="dropdown-toggle" data-toggle="dropdown" id="status_label">{{session_status["email"]}} <b class="caret"></b></a>
                        <ul class="dropdown-menu">
                        % for other_user in session_status["other_users"]:
                            <li><a href="/switch_account/{{other_user}}">{{other_user}}</a>
                        % end
                            <li><a href="/login">Add account</a>
                        </ul>
                    </li>
                    <li><a href="/logout">(Logout)</a></li>
                % else:
                    <li id="status_label">Not logged in</li>
                    <li><a href="/">(Login)</a></li>
                % end
            </ul>
        </div> <!-- nav-collapse -->
    </div> <!-- container -->
</div> <!-- navbar -->
