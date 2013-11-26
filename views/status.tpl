% include header.tpl {"session_status": session_status}
<div class="container">
    <div class="row">
        <div>
            <a href="/scan">Scan existing files</a>
            <a href="/upload">Upload scanned files</a>
        </div>
    </div>
    <div class="row">
        <div>
            <table class="table table-bordered table-striped table-hover">
                <thead>
                    <tr>
                        <th>Path</th>
                        <th>Status</th>
                        <th>Id</th>
                    </tr>
                </thead>
                <tbody>
                    % for song in songs:
                    <tr>
                        <td>
                            {{song.path}}
                        </td>
                        <td>
                            {{song.status}}
                        </td>
                        <td>
                            {{song.id}}
                        </td>
                    </tr>
                    % end
                </tbody>
            </table>
        </div>
    </div>
    <div class="row">
        <div style="text-align: center">
            <ul class="pagination">
                % prev_page = curr_page - 1
                % next_page = curr_page + 1
                % if curr_page <= 1:
                    <li class="disabled"><span>&laquo;</span></li>
                % else:
                    <li><a href="?page={{prev_page}}">&laquo;</a></li>
                % end
                % for page in range(1, num_pages + 1):
                  % if page == curr_page:
                    <li class="active"><a href="?page={{page}}">{{page}}</a></li>
                  % else:
                    <li><a href="?page={{page}}">{{page}}</a></li>
                  % end
                % end
                % if curr_page >= (num_pages + 1):
                    <li class="disabled"><span>&raquo;</span></li>
                % else:
                    <li><a href="?page={{next_page}}">&raquo;</a></li>
                % end
            </ul>
        </div>
    </div>
</div>
