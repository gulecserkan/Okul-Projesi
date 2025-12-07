Function IsPureNumber(s As String) As Boolean
    Dim i As Long, ch As String
    s = Trim(s)
    If s = "" Then Exit Function

    For i = 1 To Len(s)
        ch = Mid(s, i, 1)
        If ch < "0" Or ch > "9" Then
            Exit Function
        End If
    Next i

    IsPureNumber = True
End Function

Function IsClassHeader(t As String) As Boolean
    t = UCase(t)

    If InStr(t, "SINIF") = 0 Then Exit Function
    If InStr(t, "/") = 0 Then Exit Function
    If InStr(t, "SUBE") = 0 And InStr(t, "ŞUBE") = 0 Then Exit Function

    IsClassHeader = True
End Function





Function ExtractClass(header As String) As String

    Dim h As String, posSinif As Long, posSlash As Long
    Dim i As Long, ch As String
    Dim grade As String, branch As String

    ExtractClass = ""

    h = UCase(header)

    posSinif = InStr(h, "SINIF")
    If posSinif = 0 Then Exit Function

    grade = ""
    For i = posSinif - 1 To 1 Step -1
        ch = Mid(h, i, 1)
        If ch >= "0" And ch <= "9" Then
            grade = ch & grade
        ElseIf grade <> "" Then Exit For
        End If
    Next i
    If grade = "" Then Exit Function

    posSlash = InStr(posSinif, h, "/")
    If posSlash = 0 Then Exit Function

    branch = ""
    For i = posSlash + 1 To Len(h)
        ch = Mid(h, i, 1)
        If ch >= "A" And ch <= "Z" Then
            branch = ch
            Exit For
        End If
    Next i
    If branch = "" Then Exit Function

    ExtractClass = grade & "/" & branch

End Function


Sub BuildOgrenciTablosu_FINAL()

    Dim doc As Object, src As Object, dst As Object
    Dim sheets As Object, cursor As Object
    Dim lastRow As Long, i As Long, c As Long
    Dim dstRow As Long
    Dim currentClass As String
    Dim rowText As String
    Dim dstName As String

    doc = ThisComponent
    src = doc.getCurrentController().getActiveSheet()
    sheets = doc.Sheets
    dstName = "OgrenciTablosu"

    ' Son satır
    cursor = src.createCursor()
    cursor.gotoEndOfUsedArea(True)
    lastRow = cursor.RangeAddress.EndRow

    ' Yeni sayfa
    If sheets.hasByName(dstName) Then
        dst = sheets.getByName(dstName)
        dst.clearContents(1023)
    Else
        sheets.insertNewByName(dstName, sheets.Count)
        dst = sheets.getByName(dstName)
    End If

    ' Başlıklar
    dst.getCellByPosition(0,0).String = "ogrenci_no"
    dst.getCellByPosition(1,0).String = "ad"
    dst.getCellByPosition(2,0).String = "soyad"
    dst.getCellByPosition(3,0).String = "sinif"

    dstRow = 1
    currentClass = ""

    ' Tüm satırlar
    For i = 0 To lastRow

        ' Satırın tamamını birleştir — başlık tespiti için
        rowText = ""
        For c = 0 To 20
            rowText = rowText & " " & Trim(src.getCellByPosition(c, i).String)
        Next c

        ' --- SINIF BAŞLIĞI MI? ---
        If IsClassHeader(rowText) Then
            currentClass = ExtractClass(rowText)

        ' --- ÖĞRENCİ SATIRI MI? ---
        ElseIf currentClass <> "" And IsPureNumber(src.getCellByPosition(0, i).String) Then

            Dim no As String, ad As String, soyad As String
            no    = Trim(src.getCellByPosition(1, i).String)  ' B
            ad    = Trim(src.getCellByPosition(4, i).String)  ' E
            soyad = Trim(src.getCellByPosition(8, i).String)  ' I

            If no <> "" Then
                dst.getCellByPosition(0, dstRow).String = no
                dst.getCellByPosition(1, dstRow).String = ad
                dst.getCellByPosition(2, dstRow).String = soyad
                dst.getCellByPosition(3, dstRow).String = currentClass
                dstRow = dstRow + 1
            End If
        End If

    Next i

    MsgBox "Tamamdır! Tüm öğrenciler doğru sınıflarla aktarıldı."

End Sub

Sub DebugFull()

    Dim doc As Object, src As Object, dst As Object
    Dim sheets As Object, cursor As Object
    Dim lastRow As Long, i As Long, c As Long
    Dim dstRow As Long
    Dim rowText As String
    Dim dstName As String
    Dim A As String, B As String, E As String, Ival As String
    Dim currentClass As String
    Dim willStudent As String

    doc = ThisComponent
    src = doc.getCurrentController().getActiveSheet()
    sheets = doc.Sheets
    dstName = "DebugFull"

    ' Son satır
    cursor = src.createCursor()
    cursor.gotoEndOfUsedArea(True)
    lastRow = cursor.RangeAddress.EndRow

    ' Debug sayfası
    If sheets.hasByName(dstName) Then
        dst = sheets.getByName(dstName)
        dst.clearContents(1023)
    Else
        sheets.insertNewByName(dstName, sheets.Count)
        dst = sheets.getByName(dstName)
    End If

    ' Başlıklar
    dst.getCellByPosition(0,0).String = "row"
    dst.getCellByPosition(1,0).String = "A_value"
    dst.getCellByPosition(2,0).String = "A_len"
    dst.getCellByPosition(3,0).String = "IsPureNumber"
    dst.getCellByPosition(4,0).String = "IsClassHeader"
    dst.getCellByPosition(5,0).String = "ExtractClass"
    dst.getCellByPosition(6,0).String = "B_value"
    dst.getCellByPosition(7,0).String = "E_value"
    dst.getCellByPosition(8,0).String = "I_value"
    dst.getCellByPosition(9,0).String = "WillBeStudent"

    dstRow = 1
    currentClass = ""

    For i = 0 To lastRow

        A = src.getCellByPosition(0, i).String
        B = src.getCellByPosition(1, i).String
        E = src.getCellByPosition(4, i).String
        Ival = src.getCellByPosition(8, i).String

        ' Satır metni (başlık tespiti için)
        rowText = ""
        For c = 0 To 20
            rowText = rowText & " " & Trim(src.getCellByPosition(c, i).String)
        Next c

        ' --- Başlık mı? ---
        Dim isHead As Boolean
        isHead = IsClassHeader(rowText)

        Dim classStr As String
        If isHead Then
            classStr = ExtractClass(rowText)
            currentClass = classStr
        Else
            classStr = ""
        End If

        ' --- Öğrenci mi? ---
        Dim isStudent As Boolean
        isStudent = (currentClass <> "" And IsPureNumber(A))

        If isStudent Then
            willStudent = "TRUE"
        Else
            willStudent = "FALSE"
        End If

        ' --- Debug tablosuna yaz ---
        dst.getCellByPosition(0, dstRow).Value = i
        dst.getCellByPosition(1, dstRow).String = A
        dst.getCellByPosition(2, dstRow).Value = Len(A)

        If IsPureNumber(A) Then
            dst.getCellByPosition(3, dstRow).String = "TRUE"
        Else
            dst.getCellByPosition(3, dstRow).String = "FALSE"
        End If

        If isHead Then
            dst.getCellByPosition(4, dstRow).String = "TRUE"
            dst.getCellByPosition(5, dstRow).String = classStr
        Else
            dst.getCellByPosition(4, dstRow).String = "FALSE"
        End If

        dst.getCellByPosition(6, dstRow).String = B
        dst.getCellByPosition(7, dstRow).String = E
        dst.getCellByPosition(8, dstRow).String = Ival
        dst.getCellByPosition(9, dstRow).String = willStudent

        dstRow = dstRow + 1

    Next i

    MsgBox "DebugFull tamamlandı. DebugFull sayfasına bak."

End Sub
Sub Kontrol_Duplicate_OgrenciNo()

    Dim doc As Object, sheet As Object
    Dim cursor As Object
    Dim lastRow As Long, i As Long, j As Long
    Dim ogrNo As String
    Dim numbers()
    Dim counts()
    Dim found As Boolean
    Dim dupList As String

    doc = ThisComponent
    sheet = doc.Sheets.getByName("OgrenciTablosu")

    ' Son satır tespiti
    cursor = sheet.createCursor()
    cursor.gotoEndOfUsedArea(True)
    lastRow = cursor.RangeAddress.EndRow

    ' Dinamik dizileri başlat (0 elemanlı)
    ReDim numbers(0)
    ReDim counts(0)

    ' --- Taramaya başla ---
    For i = 1 To lastRow   ' 0 = başlık olduğu için 1'den başlıyoruz

        ogrNo = Trim(sheet.getCellByPosition(0, i).String) ' A sütunu

        If ogrNo <> "" Then

            found = False

            ' Daha önce kayıtlı mı kontrol et
            For j = 0 To UBound(numbers)
                If numbers(j) = ogrNo Then
                    counts(j) = counts(j) + 1
                    found = True
                    Exit For
                End If
            Next j

            ' Yeni numara ise ekle
            If Not found Then
                If numbers(0) = "" And UBound(numbers) = 0 Then
                    ' İlk eleman boş başlangıç durumu
                    numbers(0) = ogrNo
                    counts(0) = 1
                Else
                    ReDim Preserve numbers(UBound(numbers) + 1)
                    ReDim Preserve counts(UBound(counts) + 1)

                    numbers(UBound(numbers)) = ogrNo
                    counts(UBound(counts)) = 1
                End If
            End If

        End If
    Next i

    ' --- Duplicate olanları listele ---
    dupList = ""

    For j = 0 To UBound(numbers)
        If counts(j) > 1 Then
            dupList = dupList & numbers(j) & "  (" & counts(j) & " kez)" & Chr(10)
        End If
    Next j

    ' --- Mesaj göster ---
    If dupList = "" Then
        MsgBox "Hiçbir öğrenci numarası tekrar etmiyor. 👍", 64, "Kontrol Tamam"
    Else
        MsgBox "Tekrar eden öğrenci numaraları:" & Chr(10) & Chr(10) & dupList, 48, "Dikkat!"
    End If

End Sub

