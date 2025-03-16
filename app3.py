import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# ==================== 全局配置 ====================
PILL_OPTIONS = ["Xiaofeng Hou", "Becky Chen", "Yerik Yao"]
CLIENT_OPTIONS = ["客户A", "客户B", "客户C"]
REQUIRED_COLUMNS = ['客户名称', 'CAD', '数量', '到货日期']
EXPORT_TEMPLATE_COLUMNS = [  # 新增模板字段配置
    'Creation Date',
    'Sourcing', 
    'IO',
    'CAD',
    'Qty',
    '客户名称',
    'Request Date'
]

# ==================== 初始化函数 ====================
def initialize_session_state():
    """初始化所有session state数据"""
    for planner in PILL_OPTIONS:
        # 文件数据存储
        if f"file_{planner}" not in st.session_state:
            st.session_state[f"file_{planner}"] = pd.DataFrame(columns=REQUIRED_COLUMNS)
        
        # 批量输入数据
        if f"batch_{planner}" not in st.session_state:
            st.session_state[f"batch_{planner}"] = {
                'selected_client': '',
                'entries': []
            }
        
        # 大数量拆分临时数据
        if f"split_temp_{planner}" not in st.session_state:
            st.session_state[f"split_temp_{planner}"] = None
        
        # 已提交数据
        if f"submitted_{planner}" not in st.session_state:
            st.session_state[f"submitted_{planner}"] = pd.DataFrame(columns=REQUIRED_COLUMNS)
        
        # 提交成功提示状态
        if f"show_success_{planner}" not in st.session_state:
            st.session_state[f"show_success_{planner}"] = False

# ==================== 数据转换函数 ====================
def convert_date_column(df):
    """日期列类型转换"""
    if '到货日期' in df.columns:
        df['到货日期'] = pd.to_datetime(df['到货日期'], errors='coerce')
    return df

def convert_to_template(df):
    """转换为模板格式（新增函数）"""
    # 创建空模板
    template_df = pd.DataFrame(columns=EXPORT_TEMPLATE_COLUMNS)
    
    if not df.empty:
        # 填充可映射字段
        template_df['Creation Date'] = datetime.now().strftime('%Y-%m-%d')  # 导出时间
        template_df['CAD'] = df['CAD'].copy()
        template_df['Qty'] = df['数量'].copy()
        template_df['客户名称'] = df['客户名称'].copy()
        
        # 处理日期格式
        if '到货日期' in df.columns:
            template_df['Request Date'] = pd.to_datetime(df['到货日期']).dt.strftime('%Y-%m-%d')
        
        # 未映射字段保持空白
        template_df['Sourcing'] = ''
        template_df['IO'] = ''
    
    return template_df[EXPORT_TEMPLATE_COLUMNS]  # 保证列顺序

# ==================== 验证函数 ====================
def validate_batch(planner):
    """验证批量输入数据"""
    batch = st.session_state[f"batch_{planner}"]
    if not batch['selected_client']:
        return False, "请选择客户名称"

    for i, entry in enumerate(batch['entries'], 1):
        if not entry['CAD'].strip():
            return False, f"第{i}行CAD编号不能为空"
        if entry['数量'] is None or entry['数量'] < 0:
            return False, f"第{i}行数量无效（需≥0）"
        if not entry['到货日期']:
            return False, f"第{i}行到货日期未选择"
    return True, ""

# ==================== 页面组件 ====================
def handle_file_upload(planner):
    """文件上传组件"""
    with st.container(border=True):
        st.subheader("📤 文件上传")
        uploaded_file = st.file_uploader(
            f"上传{planner}的文件（CSV/Excel）",
            type=["csv", "xlsx"],
            key=f"upload_{planner}"
        )

        if uploaded_file:
            try:
                # 读取文件
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, engine='openpyxl')

                # 数据校验
                df = convert_date_column(df)
                missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
                if missing_cols:
                    st.error(f"缺少必要字段: {', '.join(missing_cols)}")
                    return

                # 更新数据
                st.session_state[f"file_{planner}"] = df[REQUIRED_COLUMNS]
                st.success("文件上传成功！")

                # 预览数据
                with st.expander("点击查看文件内容"):
                    st.dataframe(st.session_state[f"file_{planner}"])

            except Exception as e:
                st.error(f"文件处理错误: {str(e)}")

def handle_batch_input(planner):
    """常规批量输入页面"""
    with st.container(border=True):
        st.subheader("📝 批量录入")

        # 客户选择
        client = st.selectbox(
            "客户名称 *",
            options=[""] + CLIENT_OPTIONS,
            key=f"client_select_{planner}"
        )
        st.session_state[f"batch_{planner}"]['selected_client'] = client

        # 动态输入行
        entries = st.session_state[f"batch_{planner}"]['entries']
        if st.button("➕ 添加新行", key=f"add_row_{planner}"):
            entries.append({
                'CAD': '',
                '数量': None,
                '到货日期': datetime.today().date()
            })

        # 输入表格
        for i in range(len(entries)):
            cols = st.columns([3, 2, 3, 1])
            with cols[0]:
                entries[i]['CAD'] = st.text_input(
                    f"CAD编号 {i+1}*",
                    value=entries[i]['CAD'],
                    key=f"cad_{i}_{planner}"
                )
            with cols[1]:
                entries[i]['数量'] = st.number_input(
                    "数量*",
                    min_value=0,
                    value=entries[i]['数量'] or 0,
                    key=f"qty_{i}_{planner}"
                )
            with cols[2]:
                entries[i]['到货日期'] = st.date_input(
                    "到货日期*",
                    value=entries[i]['到货日期'],
                    format="YYYY-MM-DD",
                    key=f"date_{i}_{planner}"
                )
            with cols[3]:
                if st.button("❌", key=f"del_{i}_{planner}"):
                    entries.pop(i)
                    st.rerun()

        # 提交按钮
        if st.button("🚀 提交全部条目", type="primary", key=f"submit_batch_{planner}"):
            valid, msg = validate_batch(planner)
            if valid:
                new_data = [{
                    '客户名称': client,
                    'CAD': entry['CAD'],
                    '数量': entry['数量'],
                    '到货日期': entry['到货日期']
                } for entry in entries]

                new_df = pd.DataFrame(new_data)
                st.session_state[f"submitted_{planner}"] = pd.concat([
                    st.session_state[f"submitted_{planner}"],
                    new_df
                ], ignore_index=True)

                # 清空输入
                st.session_state[f"batch_{planner}"]['entries'] = []
                st.success(f"成功提交 {len(new_data)} 条记录！")
                st.rerun()
            else:
                st.error(f"提交失败: {msg}")

def show_history(planner):
    """显示历史记录组件"""
    with st.container(border=True):
        st.subheader("📜 历史提交记录")

        submitted_df = st.session_state[f"submitted_{planner}"].copy()
        if submitted_df.empty:
            st.info("暂无历史记录")
            return

        # 加强日期格式转换
        try:
            submitted_df['到货日期'] = pd.to_datetime(submitted_df['到货日期'], errors='coerce')
            submitted_df['到货日期'] = submitted_df['到货日期'].dt.strftime('%Y-%m-%d')
        except Exception as e:
            st.error(f"日期格式错误: {str(e)}")
            return

        st.dataframe(
            submitted_df,
            column_config={
                "数量": st.column_config.NumberColumn(format="%d 件")
            },
            hide_index=True,
            use_container_width=True
        )

        # 导出功能（修改为模板格式）
        export_df = convert_to_template(submitted_df)
        st.download_button(
            label="📥 导出当前历史记录",
            data=export_df.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"{planner}_template_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key=f"export_history_{planner}"
        )

def handle_split_input(planner):
    """大数量拆分页面（带历史记录）"""
    with st.container(border=True):
        # 显示成功提示
        if st.session_state[f"show_success_{planner}"]:
            st.success("✅ Delivery order 拆分结果已成功提交！")
            st.session_state[f"show_success_{planner}"] = False

        st.subheader("🔢 大数量拆分")

        # 拆分参数输入
        with st.form(key=f"split_form_{planner}"):
            col1, col2 = st.columns(2)
            with col1:
                client = st.selectbox(
                    "客户名称 *",
                    options=[""] + CLIENT_OPTIONS,
                    key=f"split_client_{planner}"
                )
            with col2:
                cad = st.text_input("CAD编号 *", key=f"split_cad_{planner}")

            col3, col4 = st.columns(2)
            with col3:
                total_qty = st.number_input(
                    "总数量 *",
                    min_value=1,
                    value=5000,
                    key=f"split_total_{planner}"
                )
            with col4:
                split_size = st.number_input(
                    "拆分大小 *",
                    min_value=1,
                    value=1000,
                    key=f"split_size_{planner}"
                )

            base_date = st.date_input(
                "基准到货日期",
                value=datetime.today().date(),
                format="YYYY-MM-DD",
                key=f"split_date_{planner}"
            )

            submitted = st.form_submit_button("✨ 生成拆分方案", type="primary")

        # 生成拆分方案
        if submitted:
            if not client:
                st.error("请选择客户名称")
                return
            if not cad.strip():
                st.error("请输入CAD编号")
                return

            # 计算拆分
            chunks = total_qty // split_size
            remainder = total_qty % split_size

            split_list = []
            for _ in range(chunks):
                split_list.append({
                    '客户名称': client,
                    'CAD': cad,
                    '数量': split_size,
                    '到货日期': base_date
                })
            if remainder > 0:
                split_list.append({
                    '客户名称': client,
                    'CAD': cad,
                    '数量': remainder,
                    '到货日期': base_date
                })

            st.session_state[f"split_temp_{planner}"] = pd.DataFrame(split_list)
            st.rerun()

        # 显示可编辑的临时结果
        if st.session_state[f"split_temp_{planner}"] is not None:
            st.markdown("---")
            st.subheader("🛠️ 调整拆分结果")

            edited_df = st.data_editor(
                st.session_state[f"split_temp_{planner}"],
                column_config={
                    "到货日期": st.column_config.DateColumn(
                        format="YYYY-MM-DD",
                        help="可调整单个条目的到货日期"
                    ),
                    "数量": st.column_config.NumberColumn(
                        help="可调整单个数量（≥1）",
                        min_value=1
                    )
                },
                hide_index=True,
                key=f"editor_{planner}"
            )

            # 显示统计信息
            current_total = edited_df['数量'].sum()
            st.caption(f"当前总数量: {current_total}（原始总数量: {total_qty}）")

            # 操作按钮
            col_btn1, col_btn2 = st.columns([1, 2])
            with col_btn1:
                if st.button("✅ 确认提交", type="primary", key=f"confirm_{planner}"):
                    # 数据校验
                    if edited_df['到货日期'].isnull().any():
                        st.error("存在无效的到货日期")
                        return

                    # 合并数据
                    st.session_state[f"submitted_{planner}"] = pd.concat([
                        st.session_state[f"submitted_{planner}"],
                        edited_df
                    ], ignore_index=True)

                    # 清空临时数据
                    st.session_state[f"split_temp_{planner}"] = None
                    st.session_state[f"show_success_{planner}"] = True
                    st.rerun()

            with col_btn2:
                if st.button("❌ 取消并重新生成", key=f"cancel_{planner}"):
                    st.session_state[f"split_temp_{planner}"] = None
                    st.rerun()

        # 显示历史记录
        show_history(planner)

def summary_page():
    """数据汇总页面"""
    st.title("📊 数据总览")
    st.markdown("---")

    # 合并所有数据
    all_dfs = []
    for planner in PILL_OPTIONS:
        file_df = st.session_state[f"file_{planner}"].copy()
        submitted_df = st.session_state[f"submitted_{planner}"].copy()

        # 转换日期列
        file_df['到货日期'] = pd.to_datetime(file_df['到货日期'], errors='coerce')
        submitted_df['到货日期'] = pd.to_datetime(submitted_df['到货日期'], errors='coerce')

        combined = pd.concat([file_df, submitted_df], ignore_index=True)

        if not combined.empty:
            combined["提交人"] = planner
            all_dfs.append(combined)

    if not all_dfs:
        st.warning("当前没有可显示的数据")
        return

    total_df = pd.concat(all_dfs, ignore_index=True)

    # 显示数据
    st.subheader("所有提交记录")
    st.dataframe(
        total_df,
        column_config={
            "到货日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "数量": st.column_config.NumberColumn(format="%d 件")
        },
        hide_index=True,
        use_container_width=True
    )

    # 分组统计
    st.subheader("数据分析")
    tab1, tab2 = st.tabs(["按客户统计", "按提交人统计"])

    with tab1:
        client_stats = total_df.groupby('客户名称')['数量'].sum().reset_index()
        st.bar_chart(client_stats, x='客户名称', y='数量')

    with tab2:
        planner_stats = total_df.groupby('提交人')['数量'].sum().reset_index()
        st.bar_chart(planner_stats, x='提交人', y='数量')

    # 导出功能
    st.markdown("---")
    with st.container(border=True):
        st.subheader("📥 数据导出")
        export_format = st.selectbox("导出格式", ["CSV", "Excel"])
        export_name = st.text_input("文件名", "buffer_summary")

        if st.button("生成下载文件", type="primary"):
            try:
                # 转换为模板格式（新增）
                export_df = convert_to_template(total_df)

                if export_format == "CSV":
                    csv = export_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "下载CSV",
                        data=csv,
                        file_name=f"{export_name}.csv",
                        mime="text/csv"
                    )
                else:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False)
                    st.download_button(
                        "下载Excel",
                        data=output.getvalue(),
                        file_name=f"{export_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"导出失败: {str(e)}")

# ==================== 主程序 ====================
def main():
    st.set_page_config(
        page_title="要货管理系统",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    initialize_session_state()

    # 侧边栏导航
    st.sidebar.title("导航菜单")
    page = st.sidebar.radio(
        "选择功能页面",
        ["常规录入", "大数量拆分", "数据总览"]
    )

    # 页面路由
    if page == "常规录入":
        st.title("📝 常规数据录入")
        planner = st.radio(
            "选择您的账号",
            PILL_OPTIONS,
            horizontal=True,
            key="main_planner"
        )
        st.markdown("---")
        handle_file_upload(planner)
        handle_batch_input(planner)

    elif page == "大数量拆分":
        st.title("🔢 大数量拆分")
        planner = st.radio(
            "选择您的账号",
            PILL_OPTIONS,
            horizontal=True,
            key="split_planner"
        )
        st.markdown("---")
        handle_split_input(planner)

    else:
        summary_page()

if __name__ == "__main__":
    main()