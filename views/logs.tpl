% include header.tpl {"session_status": session_status}
<div class="container">
    <div class="row">
        <div class="col-md-9 col-centered">
            <table class="table table-bordered table-striped table-hover">
                <tbody>
                % for log_line in log_lines:
                    <tr>
                        <td>
                            {{log_line}}
                        </td>
                    </tr>
                % end
                </tbody>
            </table>
        </div>
    </div>
</div>
